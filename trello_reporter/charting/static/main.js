// TODO: should we do this after the window is rendered?
$.ajax({
  url: window.location.pathname + "cumulative/",
  cache: false,
  dataType: "json"
}).done(function(data) {
  display_chart(data);
});

function display_chart(data) {
  grouped = []
  $.each(data, function(index, value) {
    if (index == 0) { return; }
    grouped.push(value[0]);
  });

  var singleAreaChart = c3.generate({
    bindto: '#chart',
    data: {
      columns: data,
      x: 'x',
      xFormat: '%Y-%m-%d',
      type: 'area-spline',
      groups: [grouped],
      order: null
    },
    axis: {
      x: {
        type: 'timeseries',
        tick: {
          format: '%Y-%m-%d'
        }
      }
    },
    legend: {
      show: true
    }
  });
}
