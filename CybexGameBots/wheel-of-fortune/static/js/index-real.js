new WOW().init()

$('#game').modal({show: true});

var check_screen = function(){
    if ($(window).width() > 600) {
        w = 500;
        h = 500;
        return w, h;
    }
    else {
        w = 300;
        h = 300;
        return w, h;
    }
};

var w, h;

check_screen();

var padding = { top: 0, right: 0, bottom: 0, left: 0 },
    // w = 500 - padding.left - padding.right,
    // h = 500 - padding.top - padding.bottom,
    r = Math.min(w, h) / 2,
    sw = 10, //stroke width
    rotation = 0,
    oldrotation = 0,
    picked = 100000,
    oldpick = [],
    color = d3.scale.category20();//category20c()

//randomNumbers = getRandomNumbers();

//http://osric.com/bingo-card-generator/?title=HTML+and+CSS+BINGO!&words=padding%2Cfont-family%2Ccolor%2Cfont-weight%2Cfont-size%2Cbackground-color%2Cnesting%2Cbottom%2Csans-serif%2Cperiod%2Cpound+sign%2C%EF%B9%A4body%EF%B9%A5%2C%EF%B9%A4ul%EF%B9%A5%2C%EF%B9%A4h1%EF%B9%A5%2Cmargin%2C%3C++%3E%2C{+}%2C%EF%B9%A4p%EF%B9%A5%2C%EF%B9%A4!DOCTYPE+html%EF%B9%A5%2C%EF%B9%A4head%EF%B9%A5%2Ccolon%2C%EF%B9%A4style%EF%B9%A5%2C.html%2CHTML%2CCSS%2CJavaScript%2Cborder&freespace=true&freespaceValue=Web+Design+Master&freespaceRandom=false&width=5&height=5&number=35#results

var awards = ['利是','大胆尝试', '财运上升', '福至心灵', '坚定', '等待机会', '以静制动', '果断', '平稳', '咸鱼翻身', '逢凶化吉', '选择', '顺遂', '贵人', '十倍币', '百倍币', '信念', '横财', '偏财', '稳步上升', '躺赚'];
var rand = awards[Math.floor(Math.random() * awards.length)]

var data = [
    { "label": "币运", "value": 1, "award": rand }, // padding
    { "label": "币运", "value": 1, "award": rand }, //font-family
    { "label": "币运", "value": 1, "award": rand }, //color
    { "label": "币运", "value": 1, "award": rand }, //font-weight
    { "label": "币运", "value": 1, "award": rand }, //font-size
    { "label": "币运", "value": 1, "award": rand }, //background-color
    { "label": "币运", "value": 1, "award": rand }, //nesting
];

var svg = d3.select('#fortune-wheel')
    .append("svg")
    .data([data])
    .attr("width", w + padding.left + padding.right + 2*sw)
    .attr("height", h + padding.top + padding.bottom + 2*sw);

var bg = svg.append("defs").append("radialGradient")
    .attr("id", "svgbg")
    .attr("cx", "50%")
    .attr("cy", "50%")
    .attr("r", "50%")
    .attr("fx", "50%")
    .attr("fy", "50%");

var bgstop = bg.append("stop")
    .attr("offset", "85%")
    .style({ "stop-color": "#EC5888", "stop-opacity": "1" });

var bgstop = bg.append("stop")
    .attr("offset", "100%")
    .style({ "stop-color": "#E04579", "stop-opacity": "1" });

var containerbg = svg.append("circle")
  .attr("cx", 0)
  .attr("cy", 0)
  .attr("r", w/2)
  .attr("fill","url(#svgbg)")
  .attr("stroke","#EDE7E8")
  .attr("stroke-width", sw )
  .attr("transform", "translate(" + (w / 2 + sw + padding.left) + "," + (h / 2 + sw + padding.top) + ")");

var container = svg.append("g")
    .attr("class", "chartholder")
    .attr("transform", "translate(" + (w / 2 + sw + padding.left) + "," + (h / 2 + sw + padding.top) + ")");


var vis = container
    .append("g");

var pie = d3.layout.pie().sort(null).value(function (d) { return 1; });

// declare an arc generator function
var arc = d3.svg.arc().outerRadius(r-sw/2);

// select paths, use arc generator to draw
var arcs = vis.selectAll("g.slice")
    .data(pie)
    .enter()
    .append("g")
    .attr("class", "slice");


arcs.append("path")
    //.attr("fill", function(d, i){ return color(i); })
    //.attr("fill", "url(#svgbg)")
    .attr("fill","transparent")
    .attr("d", function (d) { return arc(d); })
    .attr("stroke", "#fff");

// add the text
arcs.append("text").attr("transform", function (d) {
    d.innerRadius = 0;
    d.outerRadius = r;
    d.angle = (d.startAngle + d.endAngle) / 2;
    return "rotate(" + (d.angle * 180 / Math.PI - 90) + ")translate(" + (d.outerRadius - 50) + ")";
})
    .attr("text-anchor", "end")
    .text(function (d, i) {
        return data[i].label;
    });

container.on("click", spin);

var date = 0;
function timePassed(){
    if (Math.floor((new Date()-date)/60000) < 1440) {
        return false
    }
    else {
        date = new Date();
        return true
    }
}

function spin(d) {

    container.on("click", null);

    //all slices have been seen, all done
    //console.log("OldPick: " + oldpick.length, "Data length: " + data.length);
    // if (oldpick.length == data.length) {
    //     console.log("done");
    //     container.on("click", null);
    //     return;
    // }
    //only can spin again
    if (oldpick.length == "1"||(timePassed()===false)) {
        //console.log("done");
        container.on("click", null);
        d3.select("#awardresult h5")
                .text("您已抽过奖, 等24小时！");
        d3.select("#awardresult h4")
                .text("");
        d3.select("#awardresult h6")
                .text("");
        return;
    }

    var ps = 360 / data.length,
        pieslice = Math.round(1440 / data.length),
        rng = Math.floor((Math.random() * 1440) + 360);

    rotation = (Math.round(rng / ps) * ps);

    picked = Math.round(data.length - (rotation % 360) / ps);
    picked = picked >= data.length ? (picked % data.length) : picked;


    if (oldpick.indexOf(picked) !== -1) {
        d3.select(this).call(spin);
        return;
    } else {
        oldpick.push(picked);
    }

    rotation += 90 - Math.round(ps / 2);

    vis.transition()
        .duration(3000)
        .attrTween("transform", rotTween)
        .each("end", function () {

            //mark question as seen
            d3.select(".slice:nth-child(" + (picked + 1) + ") path")
                .attr("fill", "#a64666");

            //populate question

            d3.select("#awardresult h5")
            .text("今日的运势关键词: ");
            d3.select("#awardresult h4")
            .text("「" + data[picked].award + "」");
            d3.select("#awardresult h6")
            .text("按右上角分享给好友~");

            oldrotation = rotation;

            container.on("click", spin);
        });
}


var check_screen2 = function(){
    if ($(window).width() > 600) {
        return "translate(35, -25)";
    }
    else {
        return "translate(10, -25)";
    }
};

var a = check_screen2()
//make arrow

container.append("g")
    //.attr("transform", "translate(" + (w + padding.left + padding.right) + "," + ((h / 2) + padding.top) + ")")
    .attr("transform", a)
    .append("path")
    //.attr("d", "M-" + (r * .15) + ",0L0," + (r * .05) + "L0,-" + (r * .05) + "Z")
    .attr("d","M50 25L25 25L25 10z")
    //<path d="M100 50L25 93.3L25 6.7z" fill="#ff0080"/>
    .style({ "fill": "white" });
container.append("g")
    //.attr("transform", "translate(" + (w + padding.left + padding.right) + "," + ((h / 2) + padding.top) + ")")
    .attr("transform", a)
    .append("path")
    //.attr("d", "M-" + (r * .15) + ",0L0," + (r * .05) + "L0,-" + (r * .05) + "Z")
    .attr("d","M50 25L25 40L25 25z")
    //<path d="M100 50L25 93.3L25 6.7z" fill="#ff0080"/>
    .style({ "fill": "#DDDFDC" });

var check_screen3 = function(){
    if ($(window).width() > 600) {
        return 57;
    }
    else {
        return 37;    
    }
};

var b = check_screen3();

//draw spin circle
container.append("circle")
    .attr("cx", 0)
    .attr("cy", 0)
    .style({ "fill": "white", "cursor": "pointer" })
    .attr("r", b);

var check_screen4 = function(){
    if ($(window).width() > 600) {
        return 12;
    }
    else {
        return 6;
    }
};

var c = check_screen4();

var check_screen6 = function(){
    if ($(window).width() > 600) {
        return { "font-weight": "bold", "font-size": "24px" };
    }
    else {
        return { "font-weight": "bold", "font-size": "16px" };
    }
};

var d = check_screen6();

//spin text
container.append("text")
    .attr("x", 0)
    .attr("text-anchor", "middle")
    .attr("class", "centerspin")
    .text("开始")
    .attr("y", c)
    .style(d);

var check_screen5 = function(){
    if ($(window).width() > 600) {
       return 50;
    }
    else {
        return 31;
    }
};

var e = check_screen5();

container.append("circle")
    .attr("cx", 0)
    .attr("cy", 0)
    .style({ "stroke":"#F0508C","stroke-width":"3px","fill": "transparent", "cursor": "pointer" })
    .attr("r", e);

function rotTween(to) {
    var i = d3.interpolate(oldrotation % 360, rotation);
    return function (t) {
        return "rotate(" + i(t) + ")";
    };
}


function getRandomNumbers() {
    var array = new Uint16Array(1000);
    var scale = d3.scale.linear().range([360, 1440]).domain([0, 100000]);

    if (window.hasOwnProperty("crypto") && typeof window.crypto.getRandomValues === "function") {
        window.crypto.getRandomValues(array);
        console.log("works");
    } else {
        //no support for crypto, get crappy random numbers
        for (var i = 0; i < 1000; i++) {
            array[i] = Math.floor(Math.random() * 100000) + 1;
        }
    }

    return array;
}


