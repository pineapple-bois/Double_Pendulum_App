window.dash_clientside = Object.assign({}, window.dash_clientside, {
     clientside: {
         reset: function(n_clicks) {
             if (n_clicks > 0) {
                 window.location.reload();
             }
         }
     }
});