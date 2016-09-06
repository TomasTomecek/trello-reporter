/* This file is written by a person who doesn't like JavaScript and codes in python.
 * Deal with it.
 *
 * Author: Tomas Tomecek <ttomecek@redhat.com>
 */

// global variables, hold current state
var chart = null;
var previous_values = null;
var chart_data = null;
var constants = {
  datetime_format: '%Y-%m-%d %H:%M',
  day_format: '%Y-%m-%d',
};

// TODO: use PF to initialize form, stuff the code into a function and reuse in every chart
// TODO: get rid of reload functions, one function should load and reload
// class with "classmethods" to create charts
var charting = {
  reload_control: function(data) {
    chart_data.json = data.data;
    chart_data.unload = chart.columns;
    chart.load(chart_data);
  },

  control: function(data) {
    chart_data = {
      json: data["data"],
      keys: {
        value: ["date", "days"],
        x: 'date',
      },
      xFormat: constants.datetime_format,
      type: 'scatter',
      onclick: on_point_click,
      color: get_point_color,
      // colors: {
      //   hours: '#ff0000',
      //   date: '#00ff00'
      // }
    };

    chart = c3.generate({
      bindto: '#chart',
      size: {
        height: 480,
      },
      data: chart_data,
      legend: {
        show: true
      },
      axis: {
        x: {
          type: 'timeseries',
          tick: {
            // fit: true,
            format: constants.day_format,
            label: "Date"
          }
        },
        y: {
          label: 'Days',
        }
      },
      tooltip: {
        contents: get_tooltip
      },
      point: {
        r: point_size,
        focus: {
          expand: {
            enabled: false
          }
        }
      }
    });
  },

  reload_cumulative_flow: function(data) {
    chart_data.json = data.data;
    chart_data.keys.value = data.order;
    chart_data.groups = data.order
    chart_data.unload = previous_values;
    chart.load(chart_data);
    previous_values = data.order;
  },

  cumulative_flow: function(data) {
    previous_values = data.order;
    chart_data = {
      json: data["data"],
      keys: {
        value: data["order"],
        x: 'date',
      },
      xFormat: constants.datetime_format,
      type: 'area',  // area, area-spline, area-step
      groups: [data.order],
      order: null
    };

    chart = c3.generate({
      bindto: '#chart',
      data: chart_data,
      size: {
        height: 480,
      },
      axis: {
        x: {
          type: 'timeseries',
          label: 'Date',
          tick: {
            format: constants.day_format
          }
        },
        y: {
          label: '# cards',
        }
      },
      legend: {
        show: true
      },
      line: {
        connectNull: true
      }
    });
  },

  reload_burndown: function(data) {
    chart_data["json"] = data["data"];
    chart_data["unload"] = chart.columns;
    chart.load(chart_data);
  },
  burndown: function (data) {
    chart_data = {
      json: data["data"],
      keys: {
        value: ["done", "not_done", "date", "ideal"]
      },
      x: 'date',
      xFormat: constants.datetime_format,
      types: {
        "done": "bar",
        "not_done": "line",
        "ideal": "line",
      }
    };

    chart = c3.generate({
      bindto: '#chart',
      data: chart_data,
      size: {
        height: 480,
      },
      legend: {
        show: true
      },
      axis: {
        x: {
          type: 'timeseries',
          label: 'Date',
          tick: {
            format: constants.day_format
          }
        },
        y: {
          label: 'Story points',
        }
      },
      tooltip: {
        contents: get_burndown_tooltip
      },
      line: {
        connectNull: true
      }
    });
  },

  reload_velocity: function(data) {
    chart_data["json"] = data["data"];
    chart_data["unload"] = chart.columns;
    chart.load(chart_data);
  },
  velocity: function(data) {
    chart_data = {
      json: data["data"],
      keys: {
        value: ["done", "committed", "average"],
        x: "name",
      },
      types: {
        "done": "bar",
        "committed": "bar",
        "average": "area",
      }
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
        y: {
          label: "Story points"
        }
      },
    });
  },

  list_history: function(data) {
    chart_data = {
      json: data.data,
      keys: {
        value: ["cards", "story_points", "date"],
        x: 'date',
      },
      xFormat: constants.datetime_format,
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
            format: constants.day_format
          }
        },
        y: {
          label: 'Count',
        }
      },
    });
  }
};

function load_chart(callback) {
  $("#errors").hide()
  $.post(
    GLOBAL.chart_data_url,
    $('#chart-settings').serialize(),
    function(data) {
      if ("error" in data) {
        $("#errors").show()
        $("#error-content").html(data.error);
      } else {
        callback(data);
      }
    },
    'json' // I expect a JSON response
  );
}

var controller = {
  chart: function(){
    // load chart data
    load_chart(function(data) {
      charting[GLOBAL.chart_name](data);
    });

    // get chart data on form submit
    $('input#submit-button').click(function() {
      load_chart(function(data) {
        charting["reload_" + GLOBAL.chart_name](data);
      });
    });

    // focus event is still on when you're changing options, let's hook with change event
    $("div#chart-workflow div select").change(on_focus_states);
  },
  index: function(){},
  chart_without_form: function() {
    $.get(
      GLOBAL.chart_data_url,
      function(data) {
        charting[GLOBAL.chart_name](data);
      },
      'json' // I expect a JSON response
    );
  }
};

// DOM is ready, let's start the show
$(function() {
  controller[GLOBAL.view]();

  $('.datepicker').datepicker({
    format: 'yyyy-mm-dd'
  });
});

// handler for growing state machine
function on_focus_states(data) {
  var t = $(this);
  var parent_div = t.parent("div")

  // selectedIndex is better than .filter(":selected")
  if ($("#chart-workflow div").last().children("select")[0].selectedIndex > 0) {
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
        .attr("name", function(i, oldVal) {
            return oldVal.replace(/\d+/, function(m) {
                return (+m + 1);
            });
        })
    new_select
        .on("change", on_focus_states);
    // set # of forms, needed by django formsets
    $("#id_form-TOTAL_FORMS")
        .val($("#chart-workflow div.chart-settings-state-column").length);
  }
}

function get_tooltip(d, defaultTitleFormat, defaultValueFormat, color) {
  var card = this.config.data_json[d[0].source_index];
  var titleFormat = this.config.tooltip_format_title || defaultTitleFormat;
  var title = titleFormat ? titleFormat(d[0].x) : d[0].x;

  var valueFormat = this.config.tooltip_format_value || defaultValueFormat;
  var value = valueFormat(d[0].value, d[0].ratio, d[0].id, d[0].index, d);

  var tooltip = $("div#custom-chart-tooltip").html();

  tooltip = tooltip.replace("TITLE", card.name);
  tooltip = tooltip.replace("DATE", title);
  tooltip = tooltip.replace("DAYS", value);
  return tooltip;
}

function on_point_click(d, element) {
  var card_id = this.internal.config.data_json[d.source_index].id;
  window.open('/card/' + card_id + '/', '_blank');
}

function point_size(d) {
  var sizes={0:2, 1:2, 2:3, 3:4, 5:5, 8:6, 13:7};
  var point_size = this.data_json[d.source_index].size;
  for (var s in sizes) {
    if (s >= point_size) {
      return sizes[s];
    }
  }
}

function get_point_color(color, d) {
  return "#006";
}

function get_burndown_tooltip(d, defaultTitleFormat, defaultValueFormat, color) {
  var data = this.config.data_json[d[0].source_index];
  var template_b="<table class=\"c3-tooltip\"><tbody>";
  var template_e="</tbody></table>";
  var cards = "";
  data.done_cards.forEach(function(card) {
    cards += "<tr><td colspan=\"2\">" + card.name + "</td></tr>";
  });
  var response = template_b + cards +
    "<tr><td class=\"name\">Done</td><td class=\"value\">" + data.done + "</td></tr>" +
    "<tr><td class=\"name\">Not done</td><td class=\"value\">" + data.not_done + "</td></tr>" +
    template_e;
  return response;
}
