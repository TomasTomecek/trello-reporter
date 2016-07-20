// global variables, hold current state
var chart_data_url = null
var chart = null;
var chart_data = null;

// get current URL:
// window.location.pathname + "cumulative/",

// DOM is ready, let's start the show
$(function() {
  // load URL for getting data for chart
  chart_data_url = $("#chart-settings").attr('action');

  // load chart data
  $.ajax({
    url: chart_data_url,
    cache: false,
    dataType: "json"
  }).done(function(data) {
    $.each(data["all_lists"], function(idx, value) {
      $('#workflow-1-1')
          .append($("<option></option>")
          .attr("value", value)
          .text(value)
      );
    });
    display_chart(data);
  });

  // get chart data on form submit
  $('form#chart-settings input.submit-button').click(function() {
    $.post(
      chart_data_url,
      $('#chart-settings').serialize(),
      function(data) {
        chart_data["columns"] = data["data"];
        chart_data["unload"] = chart.columns;
        chart_data["groups"] = data["order"];
        chart.load(chart_data);
      },
      'json' // I expect a JSON response
    );
  });

  $("div#chart-workflow div select").focus(on_focus_states);
});

// handler for growing state machine
// FIXME: focus event is not active right away, debug & fix
function on_focus_states(data) {
  var t = $(this);
  var parent_div = t.parent("div")

  // should we add another state?
  if (parent_div.children("select").last().find(":selected").length > 0) {
    var new_select = parent_div
        .children("select")
        .last()
        .clone()
        .appendTo(parent_div)
        .val("")
        .attr("id", function(i, oldVal) {
            return oldVal.replace(/\d+$/, function(m) {
                return (+m + 1);  // +m means it's converted to `int(m) + 1`
            });
        });
    new_select
        .attr("name", new_select.attr("id"))
        .on("focus", on_focus_states);
  }

  // should we add another checkpoint?
  if ($("#chart-workflow div").last().children("select").find(":selected").length > 0) {
    var root_div = parent_div.parent("div#chart-workflow");
    root_div.append("<div class=\"chart-settings-state-column\"></div>");
    var new_div = root_div.children("div").last();
    var new_select = parent_div
        .children("select")
        .first()
        .clone()
        .appendTo(new_div)
        .val("")
        .attr("id", function(i, oldVal) {
            return oldVal.replace(/\d+/, function(m) {
                return (+m + 1);  // +m means it's converted to `int(m) + 1`
            });
        })
    new_select
        .attr("name", new_select.attr("id"))
        .on("focus", on_focus_states);
  }
}

// render cumulative chart
function display_chart(data) {
  chart_data = {
    columns: data["data"],
    x: 'x',
    xFormat: '%Y-%m-%d',
    type: 'area-spline',
    groups: [data["order"]],
    order: null
  };
  console.log(chart_data)

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
