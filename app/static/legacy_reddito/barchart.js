function BarChart(selector){
    var width = $(selector).width(),
    height = 300,
    centered,
    year = 2015,
    metric = "PIL",
    text_art = false,
    data = [],
    mouseover,
    mouseout,
    clicked,
    margin = {top: 10, right: 10, bottom: 73, left: 40};



    var createSVG = function(selector){

        var svg = d3.select(selector).append('svg')
            .attr('width', width)
            .attr('height', height)
        return svg
    }

    function chart(){

        svg = createSVG(selector)


        width = +svg.attr("width") - margin.left - margin.right,
        height = +svg.attr("height") - margin.top - margin.bottom;

        var x = d3.scale.ordinal().rangeRoundBands([0, width], .05);

        var y = d3.scale.linear().range([height, 0]);

        var xAxis = d3.svg.axis()
            .scale(x)
            .orient("bottom")
            .tickFormat(function(d){return titleCase(d)})
            .ticks(5);

        var yAxis = d3.svg.axis()
            .scale(y)
            .orient("left")
            .ticks(10);

        x.domain(data.map(function(d) { return d.region; }));
        y.domain([0, d3.max(data, function(d) { return d[year][metric]; })]);


        svg = svg.append("g")
          .attr("transform", "translate(" + margin.left + "," + margin.top + ")")

        svg.append("g")
            .attr("class", "x axis")
            .attr("transform", "translate(0," + height + ")")
            .call(xAxis)
          .selectAll("text")
            .style("text-anchor", "end")
            .attr("dx", "-10")
            .attr("dy", "5")
            .attr("transform", "rotate(-40)" );

        svg.append("g")
            .attr("class", "y axis")
            .call(yAxis)

        svg.selectAll("bar")
            .data(data)
          .enter().append("rect")
            .style("fill", "#a9ffa9")
            .attr("id", function(d){ return d.region })
            .attr("x", function(d) { return x(d.region); })
            .attr("width", x.rangeBand())
            .attr("y", function(d) { return ((y(d[year][metric])>0) ? y(d[year][metric]) : 0); })
            .attr("height", function(d) { return ((height - y(d[year][metric])>0) ? height - y(d[year][metric]) : 0) ; });




        var mouseover = function(d){

        }

        var mouseout = function(d){
        }

        chart.update = function(){

          x.domain(data.map(function(d) { return d.region; }));
          y.domain([0, d3.max(data, function(d) { return d[year][metric]; })]);

          svg.select(".y.axis")
            .transition()
            .duration(1000)
            .call(yAxis)

          svg.selectAll("rect")
            .transition()
            .duration(1000)
            .attr("x", function(d) { return x(d.region); })
            .attr("width", x.rangeBand())
            .attr("y", function(d) { return ((y(d[year][metric])>0) ? y(d[year][metric]) : 0); })
            .attr("height", function(d) { return ((height - y(d[year][metric])>0) ? height - y(d[year][metric]) : 0) ; });

          return chart;
        }

        return chart
    }



    chart.height = function(_) {
        if (!arguments.length) return height;
            height = _;
            return chart;
    };
    chart.width = function(_) {
        if (!arguments.length) return width;
            width = _;
            return chart;
    };
    chart.color = function(_) {
        if (!arguments.length) return color;
            color = _;
            return chart;
    };
    chart.year = function(_) {
        if (!arguments.length) return year;
            year = _;
            return chart;
    };
    chart.metric = function(_) {
        if (!arguments.length) return metric;
            metric = _;
            return chart;
    };
    chart.text_art = function(_) {
        if (!arguments.length) return text_art;
            text_art = _;
            return chart;
    };
    chart.mouseover = function(_) {
        if (!arguments.length) return mouseover;
            mouseover = _;
            return chart;
    };
    chart.mouseout = function(_) {
        if (!arguments.length) return mouseout;
            mouseout = _;
            return chart;
    };
    chart.clicked = function(_) {
        if (!arguments.length) return clicked;
            clicked = _;
            return chart;
    };
    chart.data = function(_) {
        if (!arguments.length) return data;
            data = _;
            return chart;
    };

    return chart
}
