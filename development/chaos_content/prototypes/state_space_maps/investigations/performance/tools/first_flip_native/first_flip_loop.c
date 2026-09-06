/* Investigation-only first-flip event driver around the vendored S1 DOP853.
 *
 * The build places a corrected temporary copy of the existing dop.c first on
 * the include path.  Including it here keeps its private dense interpolant
 * coefficients in this translation unit without changing production sources.
 */
#include "dop.c"

#include <float.h>
#include <string.h>

#define CONTEXT_SIZE 32
#define PARAMETER_COUNT 5
#define STATE_SIZE 4
#define EVENT_COUNT 4
#define TAU_VALUE 6.283185307179586476925286766559

enum context_index {
    INITIAL_THETA1 = 5,
    INITIAL_THETA2 = 6,
    INITIAL_ENERGY = 7,
    ENERGY_SCALE = 8,
    MAX_ABSOLUTE_ENERGY_ERROR = 9,
    MAX_NORMALIZED_ENERGY_DRIFT = 10,
    MAX_ANGULAR_INCREMENT = 11,
    PREVIOUS_THETA1 = 12,
    PREVIOUS_THETA2 = 13,
    EVENT_FOUND = 14,
    EVENT_INDEX = 15,
    EVENT_TIME = 16,
    ACCEPTED_POINT_COUNT = 17,
    MAXIMUM_SOLVER_STEP = 18,
    CALLBACK_ERROR = 19,
    EVENT_STATE_START = 20,
    TERMINAL_CANDIDATE_COUNT = 24,
    ROOT_ITERATIONS = 25
};

static double physical_energy(const double *y, const double *p) {
    double l1 = p[0], l2 = p[1], m1 = p[2], m2 = p[3], g = p[4];
    double kinetic = 0.5 * (m1 + m2) * l1 * l1 * y[2] * y[2]
        + 0.5 * m2 * l2 * l2 * y[3] * y[3]
        + m2 * l1 * l2 * y[2] * y[3] * cos(y[0] - y[1]);
    double potential = -(
        (m1 + m2) * g * l1 * cos(y[0]) + m2 * g * l2 * cos(y[1])
    );
    return kinetic + potential;
}

static double event_surface(int event_index, const double *y, const double *p) {
    int arm_index = event_index < 2 ? 0 : 1;
    double direction = event_index % 2 == 0 ? -1.0 : 1.0;
    double initial = arm_index == 0 ? p[INITIAL_THETA1] : p[INITIAL_THETA2];
    return direction * (y[arm_index] - initial) - TAU_VALUE;
}

static double dense_component(
    int component, double x, const double *con, int nd, double xold, double h
) {
    double s = (x - xold) / h;
    double s1 = 1.0 - s;
    double conpar = con[component + nd * 4]
        + s * (
            con[component + nd * 5]
            + s1 * (con[component + nd * 6] + s * con[component + nd * 7])
        );
    return con[component]
        + s * (
            con[component + nd]
            + s1 * (
                con[component + nd * 2]
                + s * (con[component + nd * 3] + s1 * conpar)
            )
        );
}

static void dense_state(
    double x, const double *con, int nd, double xold, double h, double *state
) {
    for (int component = 0; component < STATE_SIZE; component++) {
        state[component] = dense_component(component, x, con, nd, xold, h);
    }
}

static double dense_surface(
    int event_index, double x, const double *con, int nd, double xold,
    double h, const double *p
) {
    int arm_index = event_index < 2 ? 0 : 1;
    double direction = event_index % 2 == 0 ? -1.0 : 1.0;
    double initial = arm_index == 0 ? p[INITIAL_THETA1] : p[INITIAL_THETA2];
    return direction * dense_component(arm_index, x, con, nd, xold, h)
        - direction * initial - TAU_VALUE;
}

static double locate_root(
    int event_index, double left, double right, const double *con, int nd,
    const double *p, int *iterations
) {
    double h = right - left;
    double lower = left;
    double upper = right;
    double lower_value = dense_surface(
        event_index, lower, con, nd, left, h, p
    );
    double upper_value = dense_surface(
        event_index, upper, con, nd, left, h, p
    );
    if (lower_value == 0.0) return lower;
    if (upper_value == 0.0) return upper;
    if (!(lower_value < 0.0 && upper_value > 0.0)) return NAN;

    for (int iteration = 0; iteration < 80; iteration++) {
        double midpoint = lower + 0.5 * (upper - lower);
        double value = dense_surface(
            event_index, midpoint, con, nd, left, h, p
        );
        *iterations += 1;
        if (value >= 0.0) {
            upper = midpoint;
        } else {
            lower = midpoint;
        }
        double tolerance = 4.0 * DBL_EPSILON
            + 4.0 * DBL_EPSILON * fabs(midpoint);
        if (upper - lower <= tolerance) break;
    }
    return lower + 0.5 * (upper - lower);
}

static void update_diagnostics(double time, const double *state, double *p) {
    (void)time;
    double absolute_error = fabs(physical_energy(state, p) - p[INITIAL_ENERGY]);
    double normalized_drift = absolute_error / p[ENERGY_SCALE];
    double first_increment = fabs(state[0] - p[PREVIOUS_THETA1]);
    double second_increment = fabs(state[1] - p[PREVIOUS_THETA2]);
    p[MAX_ABSOLUTE_ENERGY_ERROR] = fmax(
        p[MAX_ABSOLUTE_ENERGY_ERROR], absolute_error
    );
    p[MAX_NORMALIZED_ENERGY_DRIFT] = fmax(
        p[MAX_NORMALIZED_ENERGY_DRIFT], normalized_drift
    );
    p[MAX_ANGULAR_INCREMENT] = fmax(
        p[MAX_ANGULAR_INCREMENT], fmax(first_increment, second_increment)
    );
    p[PREVIOUS_THETA1] = state[0];
    p[PREVIOUS_THETA2] = state[1];
    p[ACCEPTED_POINT_COUNT] += 1.0;
}

static void first_flip_observe(
    int nr, double old, double time, double *state, int n, double *con,
    int *icomp, int nd, double *p, int *error, int *stop
) {
    (void)icomp;
    if (n != STATE_SIZE || nd != STATE_SIZE || !isfinite(time)) {
        *error = 1;
    }
    for (int index = 0; index < n; index++) {
        if (!isfinite(state[index])) *error = 1;
    }
    if (*error) {
        p[CALLBACK_ERROR] = 1.0;
        *stop = -1;
        return;
    }
    if (nr == 1) return;

    p[MAXIMUM_SOLVER_STEP] = fmax(p[MAXIMUM_SOLVER_STEP], time - old);
    int candidates[EVENT_COUNT] = {0};
    int candidate_count = 0;
    for (int event_index = 0; event_index < EVENT_COUNT; event_index++) {
        double old_value = dense_surface(
            event_index, old, con, nd, old, time - old, p
        );
        double new_value = event_surface(event_index, state, p);
        if (old_value <= 0.0 && new_value >= 0.0) {
            candidates[candidate_count++] = event_index;
        }
    }

    if (candidate_count == 0) {
        update_diagnostics(time, state, p);
        return;
    }

    double earliest = INFINITY;
    int winner = -1;
    int iterations = 0;
    for (int candidate = 0; candidate < candidate_count; candidate++) {
        int event_index = candidates[candidate];
        double root = locate_root(
            event_index, old, time, con, nd, p, &iterations
        );
        if (!isfinite(root)) {
            p[CALLBACK_ERROR] = 2.0;
            *error = 1;
            *stop = -1;
            return;
        }
        if (root < earliest || (root == earliest && event_index < winner)) {
            earliest = root;
            winner = event_index;
        }
    }

    double root_state[STATE_SIZE];
    dense_state(earliest, con, nd, old, time - old, root_state);
    update_diagnostics(earliest, root_state, p);
    p[EVENT_FOUND] = 1.0;
    p[EVENT_INDEX] = (double)winner;
    p[EVENT_TIME] = earliest;
    p[TERMINAL_CANDIDATE_COUNT] = (double)candidate_count;
    p[ROOT_ITERATIONS] = (double)iterations;
    for (int index = 0; index < STATE_SIZE; index++) {
        p[EVENT_STATE_START + index] = root_state[index];
        state[index] = root_state[index];
    }
    *stop = -1;
}

/* stats: event flag/index/time, max absolute/normalized energy error,
 * max angular increment, RHS evaluations, accepted output points, maximum
 * solver step, terminal candidates, root iterations, raw DOP853 code,
 * integration endpoint, accepted steps, rejected steps. */
int first_flip_loop(
    dopri_fcn *rhs, double *state, const double *parameters, double horizon,
    double rtol, double atol, double maxstep, double *stats
) {
    double context[CONTEXT_SIZE] = {0.0};
    memcpy(context, parameters, PARAMETER_COUNT * sizeof(double));
    context[INITIAL_THETA1] = state[0];
    context[INITIAL_THETA2] = state[1];
    context[INITIAL_ENERGY] = physical_energy(state, context);
    context[ENERGY_SCALE] = context[4]
        * ((context[2] + context[3]) * context[0] + context[3] * context[1]);
    context[PREVIOUS_THETA1] = state[0];
    context[PREVIOUS_THETA2] = state[1];
    context[ACCEPTED_POINT_COUNT] = 1.0;
    context[EVENT_INDEX] = -1.0;

    double work[128] = {0.0};
    int iwork[32] = {0};
    int callback_error = 0;
    int code = 0;
    double time = 0.0;
    work[1] = 0.9;
    work[2] = 0.3;
    work[3] = 6.0;
    work[5] = maxstep;
    iwork[0] = 100000;
    iwork[4] = STATE_SIZE;
    dopri853(
        STATE_SIZE, rhs, &time, state, &horizon, &rtol, &atol, 0,
        first_flip_observe, 2, work, iwork, context, &callback_error, &code
    );

    stats[0] = context[EVENT_FOUND];
    stats[1] = context[EVENT_INDEX];
    stats[2] = context[EVENT_TIME];
    stats[3] = context[MAX_ABSOLUTE_ENERGY_ERROR];
    stats[4] = context[MAX_NORMALIZED_ENERGY_DRIFT];
    stats[5] = context[MAX_ANGULAR_INCREMENT];
    stats[6] = (double)iwork[16];
    stats[7] = context[ACCEPTED_POINT_COUNT];
    stats[8] = context[MAXIMUM_SOLVER_STEP];
    stats[9] = context[TERMINAL_CANDIDATE_COUNT];
    stats[10] = context[ROOT_ITERATIONS];
    stats[11] = (double)code;
    stats[12] = context[EVENT_FOUND] ? context[EVENT_TIME] : time;
    stats[13] = (double)iwork[18];
    stats[14] = (double)iwork[19];

    if (context[CALLBACK_ERROR] != 0.0 || callback_error != 0) return 10;
    if (context[EVENT_FOUND] != 0.0) return code == 2 ? 0 : 20 - code;
    return code == 1 ? 0 : 20 - code;
}
