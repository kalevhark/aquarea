function getEstonianWeekdays(idx) {
  const weekdays = [
    'esmaspäev', 'teisipäev', 'kolmapäev', 'neljapäev', 'reede', 'laupäev', 'pühapäev'
  ];
  return weekdays[idx];
}

function getEstonianWeekdaysShort(idx) {
  const weekdays = [
    'E', 'T', 'K', 'N', 'R', 'L', 'P'
  ];
  return weekdays[idx];
}

function* evennumbers(start, end) {
    let i = 1;
    while(i*2 <= end) {
        yield i*2;
        i += 1
    }
}

function makeHeatmapN2dalakaupaChart(container, data, title, unit) {
  let andmed = data['andmed'];
  let count = data['count'];
  let value_max = data['value_max'];
  // let unit = 'kW/h';
  Highcharts.chart(container, {
    chart: {
      type: 'heatmap',
      margin: [60, 10, 80, 50]
    },

    title: {
      text: [title, unit].join(' '),
      align: 'left',
      x: 40
    },

    subtitle: {
      text: 'n=' + count,
      align: 'left',
      x: 40
    },
    xAxis: {
      title: {
        text: null
      },
      labels: {
          format: '{value}:00'
      },
      minPadding: 0,
      maxPadding: 0,
      startOnTick: false,
      endOnTick: false,
      tickPositions: [0, 6, 12, 18, 24],
      tickWidth: 1,
      //min: 0,
      max: 23
    },
    // xAxis: {
    //   title: {
    //     text: 'tunnid'
    //   },
    //   min: 0,
    //   max: 23,
    //   labels: {
    //     align: 'left',
    //     x: 5,
    //     y: 14
    //   },
    //   showLastLabel: false,
    //   tickLength: 16,
    //   tickPositions: [...evennumbers(1, 23)],
    // },

    yAxis: {
      title: {
        text: 'nädalapäevad'
      },
      categories: ['E', 'T', 'K', 'N', 'R', 'L', 'P'],
      labels: {
        format: '{value}'
      },
      minPadding: 0,
      maxPadding: 0,
      startOnTick: false,
      endOnTick: false,
      tickPositions: [0, 2, 4, 6],
      tickWidth: 1,
      min: 0,
      max: 6,
      reversed: false
    },

    colorAxis: {
      min: 0,
      max: value_max,
      minColor: '#FFFFFF',
      maxColor: '#00FF00',
      startOnTick: false,
      endOnTick: false,
      labels:
        {
          format: '{value}'
        }
    },

    series: [{
      borderWidth: 0,
      data: andmed,
      // nullColor: '#EFEFEF',
      // colsize: 24 * 36e5, // one day
      tooltip: {
        headerFormat: [title, unit, '<br/>'].join(' '),
        // pointFormat: '{point.y} {point.x}: <b>{point.value}</b>',
        pointFormatter: function () {
          n2dalap2ev = getEstonianWeekdays(this.y);
          kellavahemik = ' kell ' + this.x + '-' + (parseInt(this.x)+1) + ':';
          value = ': <b>' + this.value + ' ' + unit + '</b>';
          elements = [n2dalap2ev, kellavahemik, value];
          return elements.join(' ');
        }
      }
    }]
  });
}

function getColorForHeatmap(n2dalap2ev, kellaaeg) {
  if ([5, 6].includes(n2dalap2ev)) {
    return "#00FF00";
  }
  let start = 0,
      end = 7
  let timeRange = Array(end - start + 1).fill().map((_, idx) => start + idx) + [22, 23]
  if (timeRange.includes(kellaaeg)) {
    return "#00FF00";
  }
  return "#00FFFF";
}

function makeHeatmapN2dalakaupa3dChart(container, data, title, unit) {
  let andmed = data['andmed'];
  const andmed3d = [];
  for (let i = 0; i < andmed.length; i++) {
    let row = {
      x: andmed[i][0],
      y: andmed[i][2],
      z: andmed[i][1],
      color: getColorForHeatmap(andmed[i][1], andmed[i][0]),
    }
    andmed3d.push(row);
  }
  let count = data['count'];
  let value_max = data['value_max'];

  // Give the points a 3D feel by adding a radial gradient
  Highcharts.setOptions({
    colors: Highcharts.getOptions().colors.map(function (color) {
      return {
        radialGradient: {
          cx: 0.4,
          cy: 0.3,
          r: 0.5
        },
        stops: [
          [0, color],
          [1, Highcharts.color(color).brighten(-0.2).get('rgb')]
        ]
      };
    })
  });

  // Set up the chart
  var chart = new Highcharts.Chart({
    chart: {
      renderTo: container,
      margin: [10, 10, 80, 50],
      type: 'scatter3d',
      animation: false,
      options3d: {
        enabled: true,
        alpha: 10,
        beta: 30,
        depth: 250,
        viewDistance: 5,
        fitToPlot: false,
        frame: {
          bottom: {size: 1, color: 'rgba(0,0,0,0.02)'},
          back: {size: 1, color: 'rgba(0,0,0,0.04)'},
          side: {size: 1, color: 'rgba(0,0,0,0.06)'}
        }
      }
    },
    title: null,
    subtitle: null,
    plotOptions: {
      scatter: {
        width: 10,
        height: 10,
        depth: 7
      }
    },
    yAxis: {
      min: 0,
      max: value_max,
      title: null
    },
    xAxis: {
      min: 0,
      max: 23,
      gridLineWidth: 1
    },
    zAxis: {
      min: 0,
      max: 6,
      // showFirstLabel: false,
      categories: ['E', 'T', 'K', 'N', 'R', 'L', 'P']
    },
    legend: {
      enabled: false
    },
    series: [{
      name: 'Data',
      colorByPoint: false,
      accessibility: {
        exposeAsGroupOnly: true
      },
      data: andmed3d
    }]
  });


  // Add mouse and touch events for rotation
  (function (H) {
    function dragStart(eStart) {
      eStart = chart.pointer.normalize(eStart);

      var posX = eStart.chartX,
        posY = eStart.chartY,
        alpha = chart.options.chart.options3d.alpha,
        beta = chart.options.chart.options3d.beta,
        sensitivity = 5,  // lower is more sensitive
        handlers = [];

      function drag(e) {
        // Get e.chartX and e.chartY
        e = chart.pointer.normalize(e);

        chart.update({
          chart: {
            options3d: {
              alpha: alpha + (e.chartY - posY) / sensitivity,
              beta: beta + (posX - e.chartX) / sensitivity
            }
          }
        }, undefined, undefined, false);
      }

      function unbindAll() {
        handlers.forEach(function (unbind) {
          if (unbind) {
            unbind();
          }
        });
        handlers.length = 0;
      }

      handlers.push(H.addEvent(document, 'mousemove', drag));
      handlers.push(H.addEvent(document, 'touchmove', drag));


      handlers.push(H.addEvent(document, 'mouseup', unbindAll));
      handlers.push(H.addEvent(document, 'touchend', unbindAll));
    }

    H.addEvent(chart.container, 'mousedown', dragStart);
    H.addEvent(chart.container, 'touchstart', dragStart);
  }(Highcharts));
}

function container_elektrilevi_n2dalakaupa_chart() {
  // Küsib andmed kuude kaupa andmed ja teeb tabeli
  let container = "container_elektrilevi_n2dalakaupa_chart";
  let loaderDiv1 = "#loaderDiv1";
  let loaderDiv3 = "#loaderDiv3";
  $.ajax({
    url: $("#" + container).attr("data-url"),
    dataType: 'json',
    beforeSend: function() {
      $(loaderDiv1).show();
      $(loaderDiv3).show();
    },
    success: function (data) {
      // console.log(data);
      makeHeatmapN2dalakaupaChart(
        container,
        data,
        'Keskmine tarbimine',
        'kW/h'
      );
      makeHeatmapN2dalakaupa3dChart(
        container + '3d',
        data,
        'Keskmine tarbimine',
        'kW/h'
      );
    },
    error: function (XMLHttpRequest, textstatus, errorThrown) {
	    alert(textstatus);
    },
    complete: function () {
      $(loaderDiv1).hide();
      $(loaderDiv3).hide();
	  }
  });
}

function container_nordpool_n2dalakaupa_chart() {
  // Küsib andmed kuude kaupa andmed ja teeb tabeli
  let container = "container_nordpool_n2dalakaupa_chart"
  let loaderDiv2 = "#loaderDiv2"
  let loaderDiv4 = "#loaderDiv4"
  $.ajax({
    url: $("#" + container).attr("data-url"),
    dataType: 'json',
    beforeSend: function() {
      $(loaderDiv2).show();
      $(loaderDiv4).show();
    },
    success: function (data) {
      // console.log(data);
      // makeNordpoolN2dalakaupaChart(container, data);
      makeHeatmapN2dalakaupaChart(
        container,
        data,
        'Nordpool keskmine hind',
        's/kWh'
      );
      makeHeatmapN2dalakaupa3dChart(
        container + '3d',
        data,
        'Nordpool keskmine hind',
        's/kWh'
      );
    },
    error: function (XMLHttpRequest, textstatus, errorThrown) {
	    alert(textstatus);
    },
    complete: function () {
      $(loaderDiv2).hide();
      $(loaderDiv4).hide();
	  }
  });
}

//Nupule vajutusega kuu edasi või tagasi valikuks
function change_month() {
  $('.changeMonth').click(function(){

    let date = Date.parse(document.getElementById("id_start_date").value);
    switch(this.id) {
      case 'kuu_edasi':
        start_date = new Date(date.getFullYear(), date.getMonth()+1, 1);
        break;
      case 'kuu_tagasi':
        start_date = new Date(date.getFullYear(), date.getMonth()-1, 1);
        break;
      default:
        break;
    }
    stopp_date = new Date(start_date.getFullYear(), start_date.getMonth()+1, start_date.getDate()-1);
    var options = { year: 'numeric', month: '2-digit', day: '2-digit' }
    document.getElementById("id_start_date").value = start_date.toLocaleDateString("et-EE", options)
    document.getElementById("id_stopp_date").value = stopp_date.toLocaleDateString("et-EE", options)
  });
}

//Tagastab eestikeelse kuunime
var getMonth = function(idx) {

  var kuud = [
	'jaanuar', 'veebruar', 'märts',
	'aprill', 'mai', 'juuni',
	'juuli', 'august', 'september',
	'oktoober', 'november', 'detsember'];

    return kuud[idx-1];
}

// $(document)
// .ajaxStart(function(){
//   document.getElementById("loader").style.display = "block";
//   $("#submit").prop("disabled", true);
//   $("#submit").hide();
//   $("#submitLoader").show();
// })
// .ajaxStop(function(){
//   $("#submit").removeAttr('disabled');
//   $("#submitLoader").hide();
//   $("#submit").show();
//   document.getElementById("loader").style.display = "none";
// });

$(document).ready(function() {
  $("#submitLoader").hide();
  change_month();
  container_elektrilevi_n2dalakaupa_chart();
  container_nordpool_n2dalakaupa_chart();
});