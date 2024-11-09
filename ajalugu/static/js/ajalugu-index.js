function container_ajalugu_index_p2evakaupa_chart() {
  let container = "container_ajalugu_index_p2evakaupa_chart"
  let loaderDiv = "#loaderDiv4"
  // Küsib andmed päevade kaupa andmed ja teeb graafiku
  $.ajax({
    url: $("#" + container).attr("data-url"),
    dataType: 'json',
    beforeSend: function() {
      $(loaderDiv).show();
    },
    success: function (data) {
	  if (data.tyhi) {
	    document.getElementById(container).innerHTML = "Perioodi andmeid pole!";
	  } else {
      // Muudame kuupäeva eestikeelseks
	    data.xAxis.categories.forEach((item, index, array) => {
        array[index] = new Date(item[0], item[1]-1, item[2], 12) ;
      });
      // Koostame andmete põhjal graafiku
	    var chart = Highcharts.chart(container, data);
	    document.getElementById("container_periood_describe").innerHTML = data.title.text;
	  }
    },
    error: function (XMLHttpRequest, textstatus, errorThrown) {
      console.log(XMLHttpRequest.responseText);
      console.log(errorThrown);
	    alert(textstatus);
    },
    complete: function () {
      $(loaderDiv).hide();
	}
  });
}


function container_ajalugu_index_kuukaupa_chart() {
  // Küsib andmed kuude kaupa andmed ja teeb graafiku
  let container = "container_ajalugu_index_kuukaupa_chart"
  let loaderDiv = "#loaderDiv1"
  $.ajax({
    url: $("#" + container).attr("data-url"),
    dataType: 'json',
    beforeSend: function() {
      $(loaderDiv).show();
    },
    success: function (data) {
	  if (data.tyhi) {
	    document.getElementById(container).innerHTML = "Perioodi andmeid pole!";
	  } else {
      // Muudame kuupäeva eestikeelseks
	    data.xAxis.categories.forEach((item, index, array) => {
        array[index] = `${getMonth(item[1])} ${item[0]}`;
      });
      // Koostame andmete põhjal graafiku
	    var chart = Highcharts.chart(container, data);
	  }
    },
    error: function (XMLHttpRequest, textstatus, errorThrown) {
	    alert(textstatus);
    },
    complete: function () {
      $(loaderDiv).hide();
	}
  });
}

function container_ajalugu_index_kuukaupa() {
  // Küsib andmed kuude kaupa andmed ja teeb tabeli
  let container = "container_ajalugu_index_kuukaupa"
  // let loaderDiv = "#loaderDiv1"
  $.ajax({
    url: $("#" + container).attr("data-url"),
    dataType: 'json',
    // beforeSend: function() {
    //   $(loaderDiv).show();
    // },
    success: function (data) {
      console.log(data);
      document.getElementById(container).innerHTML = data.kuukaupa;
    },
    error: function (XMLHttpRequest, textstatus, errorThrown) {
	    alert(textstatus);
    },
    // complete: function () {
    //   $(loaderDiv).hide();
	  // }
  });
}

function container_ajalugu_index_cop_chart() {
  // Küsib andmed kuude kaupa andmed ja teeb graafiku
  let container = "container_ajalugu_index_cop_chart"
  let loaderDiv = "#loaderDiv5"
  $.ajax({
    url: $("#" + container).attr("data-url"),
    dataType: 'json',
    beforeSend: function() {
      $(loaderDiv).show();
    },
    success: function (data) {
	  if (data.tyhi) {
	    document.getElementById(container).innerHTML = "Perioodi andmeid pole!";
	  } else {
      // Koostame andmete põhjal graafiku
	    var chart = Highcharts.chart(container, data);
	  }
    },
    error: function (XMLHttpRequest, textstatus, errorThrown) {
	    alert(textstatus);
    },
    complete: function () {
      $(loaderDiv).hide();
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

$(document)
.ajaxStart(function(){
  document.getElementById("loader").style.display = "block";
  $("#submit").prop("disabled", true);
  $("#submit").hide();
  $("#submitLoader").show();
})
.ajaxStop(function(){
  $("#submit").removeAttr('disabled');
  $("#submitLoader").hide();
  $("#submit").show();
  document.getElementById("loader").style.display = "none";
});

$(document).ready(function() {
  $("#submitLoader").hide();
  change_month();
  container_ajalugu_index_kuukaupa_chart();
  container_ajalugu_index_p2evakaupa_chart();
  container_ajalugu_index_cop_chart();
  container_ajalugu_index_kuukaupa();
});