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

function get_default_line_config() {
  return $().c3ChartDefaults().getDefaultLineConfig();
}

function get_default_bar_config() {
  return $().c3ChartDefaults().getDefaultBarConfig();
}

function get_default_area_config() {
  return $().c3ChartDefaults().getDefaultAreaConfig();
}

// initialize empty chart from patternfly
function init_chart(chart_config) {
  chart_config.bindto = '#chart';
  chart_config.size = {
    height: 480,
  };
  chart_config.legend = {
    show: true,
  };
  return chart_config;
}

// TODO: get rid of reload functions, one function should load and reload
// class with "classmethods" to create charts
var charting = {
  reload_control: function(data) {
    chart_data.json = data.data;
    chart_data.unload = chart.columns;
    chart.load(chart_data);
  },

  control: function(data) {
    var chart_defaults = init_chart(get_default_line_config());
    chart_data = {
      json: data["data"],
      keys: {
        value: ["date", "days"],
        x: 'date',
      },
      xFormat: constants.datetime_format,
      type: 'scatter',
      onclick: on_point_click,
    };

    var ch = {
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
    };
    $.extend(true, chart_defaults, ch);
    chart = c3.generate(chart_defaults);
  },

  reload_cumulative_flow: function(data) {
    chart_data.json = data.data;
    chart_data.keys.value = data.order;
    chart_data.groups = data.order
    chart_data.unload = previous_values;
    chart.load(chart_data);
    previous_values = data.order;
    c_unit = $("#id_cards_or_sp").val();
    if (c_unit == "c") {
      chart.axis.labels({y: 'Cards'});
    } else if (c_unit == "sp") {
      chart.axis.labels({y: 'Story points'});
    };
  },

  cumulative_flow: function(data) {
    var chart_defaults = init_chart(get_default_area_config());
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

    var ch = {
      data: chart_data,
      axis: {
        x: {
          type: 'timeseries',
          label: 'Date',
          tick: {
            format: constants.day_format
          }
        },
        y: {
          label: 'Cards',
        }
      },
      legend: {
        show: true
      },
      line: {
        connectNull: true
      }
    };
    $.extend(true, ch, chart_defaults);
    chart = c3.generate(ch);
  },

  reload_burndown: function(data) {
    chart_data["json"] = data["data"];
    chart_data["unload"] = chart.columns;
    chart.load(chart_data);
  },
  burndown: function (data) {
    var chart_defaults = init_chart(get_default_line_config());
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
    var ch = {
      data: chart_data,
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
    }
    $.extend(true, ch, chart_defaults)

    chart = c3.generate(ch);
  },

  reload_velocity: function(data) {
    chart_data["json"] = data["data"];
    chart_data["unload"] = chart.columns;
    chart.load(chart_data);
  },
  velocity: function(data) {
    var bar_chart_defaults = init_chart(get_default_bar_config());
    var line_chart_defaults = init_chart(get_default_line_config());
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

    var ch = {
      data: chart_data,
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
    };
    $.extend(true, ch, line_chart_defaults, bar_chart_defaults);
    ch.tooltip ={
      contents: get_velocity_tooltip
    };
    chart = c3.generate(ch);
  },

  reload_list_history: function(data) {
    chart_data["json"] = data["data"];
    chart.load(chart_data);
  },
  list_history: function(data) {
    var chart_defaults = init_chart(get_default_line_config());
    chart_data = {
      json: data.data,
      keys: {
        value: ["cards", "story_points", "date"],
        x: 'date',
      },
      xFormat: constants.datetime_format,
      type: "line"
    };
    var ch = {
      data: chart_data,
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
      }
    };
    $.extend(true, ch, chart_defaults);
    chart = c3.generate(ch);
  }
};

function load_chart(callback) {
  var errors = $("#errors");
  var error_field = errors.children().first();
  error_field.addClass("hide");
  $.post(
    GLOBAL.chart_data_url,
    $('#chart-settings').serialize(),
    function(data) {
      if ("error" in data) {
        error_field.removeClass("hide");
        var error_content = error_field.children(".error-content");
        error_content.html(data.error);
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
  $('.timepicker').datetimepicker({
    format: 'LT',
  });

  // focus event is still on when you're changing options, let's hook with change event
  $("div.state-workflow div.state-workflow-column select").change(on_focus_states);

  // simulate submit-click when user presses enter on form
  $('input[type="number"]').bind("keydown", function(e) {
    if(e.keyCode == 13) {
      $('input#submit-button').click();
    }
  });

  // don't submit forms with <enter>
  $('form').bind("keypress keydown keyup", function(e) {
    if(e.keyCode == 13) {
      e.preventDefault();
    }
  });

  // Initialize Popovers
  $(document).ready(function() {
    $('[data-toggle=popover]').popovers();
  });
});

// handler for growing state machine
function on_focus_states(data) {
  var t = $(this); // select
  var parent_div = t.parent("div"); // div.state-workflow-column
  var root_div = parent_div.parent("div.state-workflow");

  // selectedIndex is better than .filter(":selected")
  if (root_div.children("div.state-workflow-column").last().children("select")[0].selectedIndex > 0) {
    var new_div = root_div
        .children("div.state-workflow-column")
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
    parent_div.siblings("input[id$='-TOTAL_FORMS']")
        .val(root_div.find("div.state-workflow-column").length);
  }
}

function get_tooltip(d, defaultTitleFormat, defaultValueFormat, color) {
  var card = this.config.data_json[d[0].source_index];
  var titleFormat = this.config.tooltip_format_title || defaultTitleFormat;
  var title = titleFormat ? titleFormat(d[0].x) : d[0].x;

  var valueFormat = this.config.tooltip_format_value || defaultValueFormat;
  var value = valueFormat(d[0].value, d[0].ratio, d[0].id, d[0].index, d);

  var tooltip = $("div#custom-chart-tooltip").html();

  tooltip = tooltip.replace("TITLE", "#" + card.trello_card_short_id + " " + card.name);
  tooltip = tooltip.replace("DATE", title);
  tooltip = tooltip.replace("DAYS", value);
  return tooltip;
}

function on_point_click(d, element) {
  var card_id = this.internal.config.data_json[d.source_index].id;
  window.open('/card/' + card_id + '/', '_blank');
}

function point_size(d) {
  var sizes={0:2, 1:3, 2:4, 3:5, 5:6, 8:8, 13:11};
  var point_size = this.data_json[d.source_index].size;
  for (var s in sizes) {
    if (s >= point_size) {
      return sizes[s];
    }
  }
  return 15;
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

function get_velocity_tooltip(d, defaultTitleFormat, defaultValueFormat, color) {
  var data = this.config.data_json[d[0].source_index];
  var template_b="<table class=\"c3-tooltip\"><tbody>";
  var template_e="</tbody></table>";
  var t = "";
  t += "<tr><td colspan=\"2\">" + data.name + "</td></tr>";
  t += "<tr><td>Committed</td><td>" + data.committed + "</td></tr>";
  t += "<tr><td>Done</td><td>" + data.done + "</td></tr>";
  t += "<tr><td>Average</td><td>" + data.average + "</td></tr>";
  var response = template_b + t + template_e;
  return response;
}
