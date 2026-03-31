$.support.cors = true;
var gloding = true;
var gloded = false;
var gdelay = false;
//Start Market Depth Stramer 
function CloseMktStreamer() {
    document.getElementById("DivStreamer").innerHTML = "";
};


function MktStreamer(scripcode) {

    //document.getElementById("DivStreamer").innerHTML = "<table   border='0' cellpadding='0' cellspacing='0'><tr><td height='74px' valign='top'><table  border='0' cellpadding='0' cellspacing='0'><tr id ='tableStreamer' style='color:#000;vertical-align:top;font-size:11px;margin:0px;line-height:11px;background-color:#EAEAEA;'><td style='padding:2px 0px 0px 4px;color:red'>Live...</td><td align='right'  valign='top' style='padding-right:2px'><span id='CloseStreamer' style='cursor:pointer;font-weight:bold;' title='Close' onclick='CloseMktStreamer()'>x</span></td></tr><tr><td colspan='2'><iframe id='ifrmStream' src='http://search.bseindia.com/StreamerEQStkReach/StockTickerBSEPlusStkStreamer.html?scrip=" + $('[ng-controller="eqstockreachController"]').scope().scripcode + "' height='50px' width='290px' frameborder='0'></iframe></td></tr></table></iframe></td></tr></table>";
    document.getElementById("DivStreamer").innerHTML = "<iframe style='width:100%' id='ifrmStream' src='../Eqstreamer/stkreach.html?scrip=" + scripcode + "' frameborder='0'></iframe>";
    $("#DivStreamer").draggable();
}
//End Market Depth Stramer
function clearText(e, ctrl) {
    var key = e.charCode ? e.charCode : e.keyCode;
    if (key == 8) {
        var textDate = document.getElementById(ctrl);
        textDate.value = "";
    }
}
$(function () {
    $("#idtxtFromDt").datepicker({
        changeMonth: true,
        changeYear: true,
        dateFormat: "dd/mm/yy",
        maxDate: Date.now.toString()
    });
});
$(function () {
    $("#idtxtToDt").datepicker({
        changeMonth: true,
        changeYear: true,
        dateFormat: "dd/mm/yy",
        maxDate: Date.now.toString()
    });
});

//Start Eq Graph 
var graphflag = "";
var chartData = [];
var chart;
var charttype = "";

function Graph(scripcode, flag, seriesid) {

    var strfromdate = null; var strTodate = null;
    var a = new Date();
    var mon = a.getMonth();
    mon = mon + 1;
    var time = a.getDate() + "" + mon + "" + a.getFullYear() + "" + a.getHours() + "" + a.getMinutes();

    if (flag == "0") {//|| flag == "1") {
        document.getElementById('lnk5D').className = 'datelink'
        document.getElementById('lnk1M').className = 'datelink'
        document.getElementById('lnk3M').className = 'datelink'
        document.getElementById('lnk12M').className = 'datelink'
        document.getElementById('lnk6M').className = 'datelink'
        document.getElementById('lnk1').className = 'dateselected';
    }
    else if (flag == "5D" || flag == "1M" || flag == "3M" || flag == "6M" || flag == "12M") {
        document.getElementById('lnk1').className = 'datelink'
        document.getElementById('lnk5D').className = 'datelink'
        document.getElementById('lnk1M').className = 'datelink'
        document.getElementById('lnk3M').className = 'datelink'
        document.getElementById('lnk6M').className = 'datelink'
        document.getElementById('lnk12M').className = 'datelink'
        document.getElementById('lnk' + flag).className = 'dateselected';
    }
    if (flag == "1") {//(seriesid == "DT" && flag == "1") {
        if (datevalidate()) {

            var fromdt = document.getElementById("idtxtFromDt").value;
            var todate = document.getElementById("idtxtToDt").value;
            var arrFrmdate = fromdt.split('/');
            strfromdate = arrFrmdate[2] + arrFrmdate[1] + arrFrmdate[0];
            var arrTodate = todate.split('/');
            strTodate = arrTodate[2] + arrTodate[1] + arrTodate[0];
            document.getElementById("idtxtFromDt").value = '';
            document.getElementById("idtxtToDt").value = '';


        }
        else { return; }
    }

    var apiurl;
    var data = [];
    var CurrDate;
    var PreClose;
    var Minlow;
    var Maxhigh;
    var a1 = "Date,Pre-open,Value\n";

    apiurl = newapi_domain + "StockReachGraph/w";
    gloding = true;
    gloded = false;
    $.ajax({
        type: "GET",
        url: apiurl, //"http://api.bseindia.com/BseIndiaAPI/api/StockReachGraph/w",
        data: { scripcode: scripcode, flag: flag, fromdate: strfromdate, todate: strTodate, seriesid: seriesid },

        //contentType: "application/json; charset=utf-8",
        contenttype: "application/json; charset=utf-8",//"text/html\r\n\r\n",
        crossDomain: true,
        //dataType: "json",
        async: false,

        success: function (data) {

            if (typeof (chart) !== "undefined") {
                chartdiv.clearText = "";
            }
            if (graphflag == flag) {
                chartData = data;
                chartData.Data = (chartData.Data);
                
                    chart.dataProvider = chartData.Data;//AmCharts.parseJSON(data);
                    generateChartData(data, flag, seriesid);
                    chart.validateData();
                
            }
            else {
                graphflag = flag
                generateChartData(data, flag, seriesid);
            }
            //dyGraph(data.d);
            gloded = true;
            gdelay = false;
            gloding = false;
        },
    });
}

function generateChartData(Bdata, flag, seriesid) {
   
    chartData = Bdata;
    chartData.Data = $.parseJSON(chartData.Data);
    if (!chartData.Data || chartData.Data === '[]' || chartData.Data === '') {
        $('#DivNoData').css('visibility', 'visible');
        $(".zoom").css('display', 'none');
        $("#DivNoData").css("height", 250);
        $("#DivNoData").css("padding-top", 95);
        $('#chartdiv').css('display', 'none');
    }
    else
    {
        $('#DivNoData').css('visibility', 'hidden');
        $(".zoom").css('display', '');
        $("#DivNoData").css("height", 0);
        $("#DivNoData").css("padding-top", 0);
        $('#chartdiv').css('display', '');

        var guideline = {};
        var balntxt = "";
        var lblPrice = "";
        var lblVolumne = "";


        if (flag == '1M' || flag == '3M' || flag == '6M' || flag == '12M' || flag == "1") {//seriesid == 'DT') {
            groupToPeriods = ['mm', 'dd'];
            guideline = {};
            balntxt = "<b>Date:[[category]]</b>";
            lblVolumne = "<b>Volumn:[[vole]]</b>";
        }
        else if (flag == '5D') {

            groupToPeriods = ['mm', 'dd'];
            guideline = {};
            balntxt = "<b>Date:[[category]]</b>";
        }
        else {
            var PreClose = chartData.PrevClose;
            groupToPeriods = ['mm'];
            balntxt = "<b>Time:[[category]]</b>";
            guideline = {
                "value": PreClose,
                "lineAlpha": 0.8,
                "lineColor": "#c00",
                "position": "right"
            };
        }

        charttype = flag;
        if (flag == "1") {
            flag = "0";
        }
        chart = AmCharts.makeChart("chartdiv", {
            "type": "stock",
            "theme": "light",
            "visibility": "hidden",
            "categoryAxesSettings": {
                "minPeriod": "mm",
                "groupToPeriods": groupToPeriods,
                "equalSpacing": true,
            },

            "dataSets": [{
                "color": "#0d98e2",

                "fieldMappings": [{
                    "fromField": "vale1",
                    "toField": "vale1"
                }, {
                    "fromField": "vole",
                    "toField": "vole"
                }],

                "dataProvider": chartData.Data,
                "categoryField": "dttm",
                "categoryAxis": {
                    "dateFormats": [{
                        "period": 'fff',
                        "format": 'HH:mm:ss'
                    }, {
                        "period": 'ss',
                        "format": 'HH:mm:ss'
                    }, {
                        "period": 'mm',
                        "format": 'HH:mm'
                    }, {
                        "period": 'HH',
                        "format": 'HH:mm'
                    }, {
                        "period": "DD",
                        "format": "DD"
                    }, {
                        "period": "WW",
                        "format": "MMM DD"
                    }, {
                        "period": "MM",
                        "format": "MMM"
                    }, {
                        "period": "YYYY",
                        "format": "YYYY"
                    }],
                    "parseDates": true,
                    "autoGridCount": false,
                    "axisColor": "#555555",
                    "gridAlpha": 0.1,
                    "gridColor": "#FFFFFF",
                    "gridCount": 50,

                },
            }],
            "panels": [{
                "showCategoryAxis": false,
                "percentHeight": 100,
                "stockGraphs": [{
                    "id": "g1",
                    "valueField": "vale1",
                    "title": "Price",
                    "comparable": false,
                    "lineColor": "#0192ee",
                    "fillAlphas": 0.6,
                    "useDataSetColors": true,
                    "lineThickness": 1,
                    "balloonText": "[[title]]:<b>[[value]]</b>   <br>" + balntxt,
                    "compareGraphBalloonText": "[[title]]:<b>[[value]]</b>",
                }], "valueAxes": [{
                    "includeGuidesInMinMax": true,
                    "guides": [{

                        "value": PreClose,
                        "lineAlpha": 0.8,
                        "lineColor": "#c00",
                        "lineThickness": 1,
                        "position": "right"
                    }
                    ]
                }
                ],
                "stockLegend": {
                    "balloonText": "[[title]]:<b>[[value]]</b>",
                    "compareGraphBalloonText": "[[title]]:<b>[[value]]</b>"
                }

            }, {

                "percentHeight": 70,
                "stockGraphs": [{
                    "id": "g2",
                    "valueField": "vole",
                    "title": "Volume",
                    "comparable": true,
                    "type": "column",
                    "showBalloon": true,
                    "lineColor": "#009933",
                    "useDataSetColors": false,
                    "fillAlphas": 1.0,
                    "valueAxis": "v2",
                    "lineThickness": 1,
                    "columnWidth": 0.50,
                    "balloonText": "[[title]]:<b>[[value]]</b>  <br>" + balntxt,
                    "compareGraphBalloonText": "[[title]]:<b>[[value]]</b>",
                }],

                "stockLegend": {
                    "periodValueTextRegular": "[[value.close]]"
                },
                "valueAxes": [{
                    "includeGuidesInMinMax": true,
                    "guides": [guideline],
                },
                {
                    "id": "v1",
                    "title": "Price",
                    "position": "left",
                    "gridThickness": 0

                },
                {
                    "id": "v2",
                    "position": "left",
                    "gridThickness": 0,
                    "labelFunction": function (value, valueText, valueAxis) {
                        if (value >= 1000000) {
                            var a = (value / 1000000).toFixed(0);
                            var b;
                            if (parseInt(a) > parseInt(0)) { b = a + 'M'; }
                            else { b = valueText }
                            return b;

                        }
                        else {
                            var a = (value / 1000).toFixed(0);
                            var b;
                            if (parseInt(a) > parseInt(0)) { b = a + 'k'; }
                            else { b = valueText }
                            return b;
                        }
                    }
                }],
            }],
            "panelsSettings": {
                "marginLeft": 10,
                "marginRight": 15,

            },
            "chartScrollbarSettings": {
                "enabled": false
            },

            "valueAxesSettings": {
                "inside": true,
                "autoMargins": true,

            },

            "chartCursorSettings": {
                "fullWidth": false,
                "valueLineEnabled": true,
                "valueLineAlpha": 0,
                "pan": false,
                "balloonText": balntxt,
                "categoryBalloonEnabled": false,
                "valueBalloonsEnabled": true,
                "fullWidth": false,
                "cursorAlpha": 0.1,
                "valueLineAlpha": 0
            },


            "dataSetSelector": {
                "divId": "selector"
            },

            "export": {
                "enabled": true
            }
        });

        AmCharts.checkEmptyData = function (chart) {
            if (chart.dataSets == undefined || 0 == chart.dataSets[0].dataProvider.length) {
                $('#DivNoData').css('visibility', 'visible');
                $(".zoom").css('display', 'none');
                $("#DivNoData").css("height", 250);
                $("#DivNoData").css("padding-top", 95);
                $('#chartdiv').css('display', 'none');
            }

        }

        $(".zoom").css('display', 'block');
        AmCharts.checkEmptyData(chart);
    }
}
function refresh_graph(code, flag, seriesid) {
    Graph(code, flag, seriesid);
}

function leadingZero(value) {
    if (value < 10) {
        return "0" + value.toString();
    }
    return value.toString();
}

function datevalidate() {

    var status = true;
    var fromdt = document.getElementById("idtxtFromDt").value;
    var todate = document.getElementById("idtxtToDt").value;
    var arrFrmdate = fromdt.split('/');
    strfromdate = arrFrmdate[2] + arrFrmdate[1] + arrFrmdate[0];
    var arrTodate = todate.split('/');
    strTodate = arrTodate[2] + arrTodate[1] + arrTodate[0];
    var d = new Date();
    var day = d.getDate();
    var mon = d.getMonth() + 1;
    var year = d.getFullYear();
    var dateformat = year + leadingZero(mon) + leadingZero(day);
    if (fromdt == "" && todate == "") {

        alert('Please Select Date.');
        status = false;
        return status;
    }
    else {
        return status;
    }
    if (fromdt == "" && fromdt == "") {
        alert('Please Select From Date.');
        status = false;
        return status;
    }
    else {
        return status;
    }
    if (todate == "") {
        alert('Please Select To Date.');
        return false;
    }
    if (fromdt != "") {
        if (parseInt(strfromdate) > parseInt(dateformat)) {
            alert('You cannot select future date.')
            document.getElementById("idtxtFromDt").value = '';
            status = false;
            return status;
        }
        else {

            return status;
        }
    }
    if (todate != "") {
        if (parseInt(strTodate) > parseInt(dateformat)) {
            alert('You cannot select future date.')
            document.getElementById("idtxtToDt").value = '';
            return false;
        }
        else {
            return status;
        }
    }
    if (strfromdate != '' && strTodate != '') {
        if (parseInt(strfromdate) > parseInt(strTodate)) {
            alert('Start Date cannot be greater than End Date.');
            document.getElementById("idtxtFromDt").value = '';
            document.getElementById("idtxtToDt").value = '';
            return false;
        }
        else { return status; }
    }
    if (strfromdate != '' && strTodate != '') {
        if (parseInt(strfromdate) == parseInt(strTodate)) {
            alert('Cannot select same date.');
            document.getElementById("idtxtFromDt").value = '';
            document.getElementById("idtxtToDt").value = '';
            return false;
        }
        else { return status; }
    }
    return status;
}

function zoomOut() {
    chart.zoomOut();
}
//End Eq Graph 

(function ($) {

    $.fn.doubletap = $.fn.doubletap || function (handler, delay) {
        delay = delay == null ? 300 : delay;
        this.bind('touchend', function (event) {
            var now = new Date().getTime();
            // The first time this will make delta a negative number.
            var lastTouch = $(this).data('lastTouch') || now + 1;
            var delta = now - lastTouch;
            if (delta < delay && 0 < delta) {
                // After we detect a doubletap, start over.
                $(this).data('lastTouch', null);
                if (handler !== null && typeof handler === 'function') {
                    handler(event);
                }
            } else {
                $(this).data('lastTouch', now);
            }
        });
    };

})(jQuery);

$('#chartdiv').doubletap(function (e) {
    zoomOut();
});

$(document).ready(function () {
    $("#DaySlider").slider({ disabled: true });
    $("#WeekSlider").slider({ disabled: true });
    $("#DaySlider").slider("option", "classes.ui-slider", "slidebar");
    $("#WeekSlider").slider("option", "classes.ui-slider", "slidebar");
});

/**
 * Custom legend manipulation functions
 */
function resetLegend() {
    buildLegend(getLegendData());
}

function buildLegend(data) {
    // clear legend
    var legend = document.getElementById("legend");
    legend.innerHTML = "";
    if (data != undefined) {
        // add items
        for (var id in data) {
            if (!data.hasOwnProperty(id))
                continue;
            var ds = data[id];

            // create legend item
            var item = document.createElement("div");
            item.className = "item";
            // create line
            var line = document.createElement("div");
            line.className = "line";

            // create graphs
            for (var g = 0; g < ds.graphs.length && g < 3; g++) {
                var graph = ds.graphs[g];

                line.innerHTML += "  " + graph.title + ": " + graph.value;
            }

            // add to item
            item.appendChild(line);

            // append item to legend
            legend.appendChild(item);
        }
    }
}

function getLegendData(dataIndex) {
    var sets = {};
    for (var p = 0; p < chart.panels.length; p++) {
        var panel = chart.panels[p];
        var graphTitles = [];
        for (var g = 0; g < panel.stockGraphs.length; g++) {
            var graph = panel.stockGraphs[g];
            graphTitles[graph.valueField] = graph.title;
        }
        if (panel.graphs != undefined) {
            for (var g = 0; g < panel.graphs.length; g++) {
                var graph = panel.graphs[g];
                var ds = graph.dataSet === undefined ? chart.mainDataSet : graph.dataSet;
                if (!sets.hasOwnProperty(ds.id))
                    sets[ds.id] = {
                        "title": ds.title,
                        "color": ds.color,
                        "graphs": []
                    }
                var index = dataIndex !== undefined ? dataIndex : graph.data.length - 1;//-1;
                if (graph.data[index] === undefined) {
                    sets[ds.id].graphs.push({
                        "title": graphTitles[graph.valueField]
                    });
                } else {
                    //console.log(graph.dataProvider);
                    value = graph.data[index].dataContext.dataContext[graph.valueField];
                    dttm = new Date(graph.data[index].dataContext.dataContext["dttm"]);
                    if (graph.dataProvider !== undefined)
                        value = graph.dataProvider[index].dataContext[graph.valueField];
                    if (g == 0) {
                        if (charttype == "0") {
                            sets[ds.id].graphs.push({
                                "title": "Time",//graphTitles[graph.valueField],
                                "value": ((dttm.getHours()) + ":" + dttm.getMinutes())
                            });
                        }
                        else {
                            sets[ds.id].graphs.push({
                                "title": "Date",//graphTitles[graph.valueField],
                                "value": ((dttm.getMonth() + 1) + "-" + dttm.getDate() + "-" + dttm.getFullYear())
                            });
                        }
                    }
                    sets[ds.id].graphs.push({
                        "title": graphTitles[graph.valueField],
                        "value": value
                        //"value": graph.dataProvider[index].dataContext[graph.valueField]
                    });
                }

            }
        }
    }
    return sets;
}


function MCXUrl() {
    window.open("/D90/Header/MCXPopUp.html", "_blank", "toolbar=no, scrollbars=yes, resizable=no, top=100, left=500, width=400, height=400");
}

