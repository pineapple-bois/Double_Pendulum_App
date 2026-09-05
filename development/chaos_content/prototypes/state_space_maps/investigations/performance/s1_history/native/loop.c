/* Experimental single-cell driver. No changes to the vendored DOP853. */
#include "dop.h"
#include <float.h>
#include <string.h>

/* rpar: physical parameters[5], initial energy, energy scale, max drift,
 * previous observation time, maximum observed step. ipar: observation error. */
static double energy(const double *y, const double *p) {
    double l1=p[0], l2=p[1], m1=p[2], m2=p[3], g=p[4];
    double kinetic = 0.5*(m1+m2)*(l1*l1)*(y[2]*y[2])
        + 0.5*m2*(l2*l2)*(y[3]*y[3])
        + m2*l1*l2*y[2]*y[3]*cos(y[0]-y[1]);
    double potential = -((m1+m2)*g*l1*cos(y[0])+m2*g*l2*cos(y[1]));
    return kinetic + potential;
}

static void observe(int nr, double old, double t, double *y, int n,
                    double *con, int *icomp, int nd, double *p, int *error,
                    int *stop) {
    (void)old; (void)con; (void)icomp; (void)nd;
    if (!isfinite(t)) *error = 1;
    for (int j=0; j<n; j++) if (!isfinite(y[j])) *error = 1;
    if (nr > 1) {
        double step = t-p[8];
        if (!(step > 0)) *error = 1;
        p[9] = fmax(p[9], step);
    }
    p[8] = t;
    double drift = fabs(energy(y,p)-p[5])/p[6];
    if (!isfinite(drift)) *error = 1;
    p[7] = fmax(p[7], drift);
    if (*error) *stop = -1;
}

/* Output columns: stretch, log, cumulative log, rate. stats: drift, norm
 * error, actual maximum step, RHS calls. Return 0 or explicit failure code.
 * rhs is the existing compiled production kernel exposed with numba.cfunc.
 * reset is a compiled NumPy-compatible normalization/chart callback. */
typedef int reset_fcn(double *, double, double *, double *);
int s1_loop(dopri_fcn *rhs, reset_fcn *reset, double *y, const double *params,
            const double *boundaries, int cycles, double rtol, double atol,
            double maxstep, double tc, double *out, double *stats) {
    double p[10] = {0};
    memcpy(p, params, 5*sizeof(double));
    p[5] = energy(y,p);
    p[6] = p[4]*((p[2]+p[3])*p[0]+p[3]*p[1]);
    double cumulative = 0;
    for (int cycle=0; cycle<cycles; cycle++) {
        double work[109] = {0};
        int iwork[21] = {0}, error=0, code=0;
        work[1]=0.9; work[2]=0.3; work[3]=6.0;
        work[5]=maxstep; /* beta=0, first_step=0; restart every segment. */
        iwork[0]=100000;
        double t=boundaries[cycle], end=boundaries[cycle+1];
        dopri853(8,rhs,&t,y,&end,&rtol,&atol,0,observe,1,work,iwork,p,&error,&code);
        stats[3] += iwork[16];
        if (error) return 10;
        if (code != 1) return 20-code;
        if (fabs(t-end)>1e-13) return 30;
        stats[2] = p[9];
        if (p[9]>maxstep+64*DBL_EPSILON*fmax(1.0,fabs(maxstep))) return 40;
        double stretch=0, normerror=0;
        if (reset(y,tc,&stretch,&normerror)) return 50;
        double increment=log(stretch);
        cumulative += increment;
        out[4*cycle]=stretch;
        out[4*cycle+1]=increment;
        out[4*cycle+2]=cumulative;
        out[4*cycle+3]=cumulative/end;
        stats[1]=fmax(stats[1],normerror);
    }
    stats[0]=p[7];
    return 0;
}
