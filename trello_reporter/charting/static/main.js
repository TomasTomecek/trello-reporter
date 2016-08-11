// global variables, hold current state
var chart_data_url = null;
var chart = null;
var previous_values = null;
var chart_data = null;
var cache = {
  cards: {},  // card_id -> response from api
  card_indexes: {},  // c3_index -> response from api
  lists: {},
  boards: {}
 };

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
    if (chart_data_url.indexOf("control") > -1) {
      render_control_chart(data);
    } else if (chart_data_url.indexOf("cumulative") > -1) {
      render_cumulative_chart(data);
    } else if (chart_data_url.indexOf("burndown") > -1) {
      render_burndown_chart(data);
    } else if (chart_data_url.indexOf("velocity") > -1) {
      render_velocity_chart(data);
    } else if (chart_data_url.indexOf("list-history") > -1) {
      render_list_history_chart(data);
    }
    $.each(data["all_lists"], function(idx, value) {
      $('#workflow-1')
          .append($("<option></option>")
          .attr("value", value)
          .text(value)
      );
    });
  });

  // get chart data on form submit
  $('form#chart-settings input.submit-button').click(function() {
    $.post(
      chart_data_url,
      $('#chart-settings').serialize(),
      function(data) {
        if (chart_data_url.indexOf("control") > -1) {
          alert("not implemented yet");
        } else if (chart_data_url.indexOf("cumulative") > -1) {
          reload_cumulative_chart(data);
        } else if (chart_data_url.indexOf("burndown") > -1) {
          reload_burndown_chart(data);
        }
      },
      'json' // I expect a JSON response
    );
  });

  $("div#chart-workflow div select").focus(on_focus_states);
});

// handler for growing state machine
function on_focus_states(data) {
  var t = $(this);
  var parent_div = t.parent("div")

  // // should we add another state?
  // if (parent_div.children("select").last().find(":selected").length > 0) {
  //   var new_select = parent_div
  //       .children("select")
  //       .last()
  //       .clone()
  //       .appendTo(parent_div)
  //       .val("")
  //       .attr("id", function(i, oldVal) {
  //           return oldVal.replace(/\d+$/, function(m) {
  //               return (+m + 1);  // +m means it's converted to `int(m) + 1`
  //           });
  //       });
  //   new_select
  //       .attr("name", new_select.attr("id"))
  //       .on("focus", on_focus_states);
  // }

  // should we add another checkpoint?
  if ($("#chart-workflow div").last().children("select").find(":selected").length > 0) {
    var root_div = parent_div.parent("div#chart-workflow");
    var new_div = root_div
        .children("div.chart-settings-state-column")
        .last()
        .clone()
        .appendTo(root_div)
    var new_select = new_div
        .children("select")
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

function get_selected_card_id(c3, d) {
  return c3.config.data_json[d[0].index].id;
}

function get_tooltip(d, defaultTitleFormat, defaultValueFormat, color) {
  var card_id = get_selected_card_id(this, d)
  var tooltip = $("div#custom-chart-tooltip").html();

  if (!(card_id in cache.cards)) {
    $.ajax({
      url: "/api/v0/card/" + card_id + "/",
      dataType: "json",
      async: false,
    }).done(function(data) {
      cache.cards[card_id] = data;
      cache.card_indexes[d[0].index] = data;
    });
  }
  tooltip = tooltip.replace("TITLE", cache.cards[card_id].name);
  return tooltip;
}

function on_point_click(d, element) {
  var card_id = cache.card_indexes[d.index].id;  // FIXME: race for the data to get there
  window.open('/card/' + card_id + '/', '_blank');
}

function point_size(d) {
  return Math.random() * 5;
}

function get_point_color(color, d) {
  return "#006";
}

function render_control_chart(data) {
  chart_data = {
    json: data["data"],
    keys: {
      value: ["date", "hours"],
      x: 'date',
    },
    xFormat: '%Y-%m-%d',
    type: 'scatter',
    onclick: on_point_click,
    color: get_point_color,
    colors: {
      hours: '#ff0000',
      date: '#00ff00'
    }
  };

  chart = c3.generate({
    bindto: '#chart',
    data: chart_data,
    legend: {
      show: true
    },
    axis: {
      x: {
        type: 'timeseries',
        tick: {
          fit: true,
          format: '%Y-%m-%d'
        }
      },
      y: {
        label: 'hours',
      }
    },
    tooltip: {
      contents: get_tooltip
    },
    // point: {
    //   r: point_size
    // }
  });
}

function reload_cumulative_chart(data) {
  chart_data.json = data.data;
  chart_data.keys.value = data.order;
  chart_data.groups = data.order
  chart_data.unload = previous_values;
  chart.load(chart_data);
  previous_values = data.order;
}

function render_cumulative_chart(data) {
  previous_values = data.order;
  chart_data = {
    json: data["data"],
    keys: {
      value: data["order"],
      x: 'date',
    },
    xFormat: '%Y-%m-%d %H:%M',
    type: 'area',  // area, area-spline, area-step
    groups: [data.order],
    order: null
  };

  chart = c3.generate({
    bindto: '#chart',
    data: chart_data,
    axis: {
      x: {
        type: 'timeseries',
      }
    },
    legend: {
      show: true
    },
    line: {
      connectNull: true
    }
  });
}

function reload_burndown_chart(data) {
  chart_data["json"] = data["data"];
  chart_data["unload"] = chart.columns;
  chart.load(chart_data);
}

function render_burndown_chart(data) {
  chart_data = {
    json: data["data"],
    keys: {
      value: ["done", "not_done", "date"]
    },
    x: 'date',
    xFormat: '%Y-%m-%d',
    types: {
      "done": "line",
      "not_done": "line",
    }
  };

  chart = c3.generate({
    bindto: '#chart',
    data: chart_data,
    legend: {
      show: true
    },
    axis: {
      x: {
        type: 'timeseries',
        tick: {
          format: '%Y-%m-%d'
        }
      },
      y: {
        label: 'hours',
      }
    },
  });
}

function render_velocity_chart(data) {
  chart_data = {
    json: data["data"],
    keys: {
      value: ["story_points", "cards_num"],
      x: "name",
    },
    type: "bar"
  };

  chart = c3.generate({
    bindto: '#chart',
    data: chart_data,
    legend: {
      show: true
    },
    bar: {
      width: {
          ratio: 0.5
      }
    },
    axis: {
      x: {
        label: "Sprint",
        type: "category"
      },
    },
  });
}

function render_list_history_chart(data) {
  chart_data = {
    json: data["data"],
    keys: {
      value: ["count", "date"],
      x: 'date',
    },
    xFormat: '%Y-%m-%d %H:%M',
    type: "line"
  };

  chart = c3.generate({
    bindto: '#chart',
    data: chart_data,
    legend: {
      show: true
    },
    axis: {
      x: {
        type: 'timeseries',
        label: 'Time',
        tick: {
          format: '%Y-%m-%d %H:%M'
        }
      },
      y: {
        label: 'Count',
      }
    },
  });
}
