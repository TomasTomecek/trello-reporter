var chart_data_url = null
var chart = null;
var chart_data = null;

// window.location.pathname + "cumulative/",

// DOM is ready, let's start the show
$(function() {
  chart_data_url = $("#chart-settings").attr('action');
  $.ajax({
    url: chart_data_url,
    cache: false,
    dataType: "json"
  }).done(function(data) {
    display_chart(data);
  });

  $('form#chart-settings input.submit-button').click(function() {
    $.post(
      chart_data_url,
      $('#chart-settings').serialize(),
      function(data) {
        chart_data["columns"] = data
        chart.load(chart_data);
      },
      'json' // I expect a JSON response
    );
  });
});


function display_chart(data) {
  grouped = []
  $.each(data, function(index, value) {
    if (index == 0) { return; }
    grouped.push(value[0]);
  });

  chart_data = {
    columns: data,
    x: 'x',
    xFormat: '%Y-%m-%d',
    type: 'area-spline',
    groups: [grouped],
    order: null
  };

  chart = c3.generate({
    bindto: '#chart',
    data: chart_data,
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
