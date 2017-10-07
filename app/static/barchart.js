var myX
var myY
var myDomain
var test

function BarChart(selector) {
    var width = $(selector).width(),
        height = 600,
        centered,
        data = [],
        color = 'url(#svgGradient)',
        color_selected = '#464647',
        color_hover = '#CACACA',
        mouseover,
        mouseout,
        clicked,
        event_listner = {},
        margin = { top: 30, right: 10, bottom: 73, left: 100 };



    var createSVG = function(selector) {
        var svg = d3.select(selector).append('svg')
            .attr('width', width)
            .attr('height', height)
        return svg
    }

    function chart() {

        var svg = createSVG(selector);
        var udm = data[0].UDM;

        var defs = svg.append("defs");
        var gradient = defs.append("linearGradient")
            .attr("id", "svgGradient")
            .attr("x1", "0%")
            .attr("x2", "100%")
            .attr("y1", "0%")
            .attr("y2", "0%");

        gradient.append("stop")
            .attr('class', 'start')
            .attr("offset", "0%")
            .attr("stop-color", "#adefad")
            .attr("stop-opacity", 1);

        gradient.append("stop")
            .attr('class', 'end')
            .attr("offset", "100%")
            .attr("stop-color", "#79e779")
            .attr("stop-opacity", 1);


        data.sort(function(x, y) {
            return d3.descending(x.Dato, y.Dato);
        })


        width = +svg.attr("width") - margin.left - margin.right,
            height = +svg.attr("height") - margin.top - margin.bottom;

        var y = d3.scale.ordinal().rangeRoundBands([0, height], .05);

        var x = d3.scale.linear().range([0, width]);

        var xAxis = d3.svg.axis()
            .scale(x)
            .orient("bottom")
            .tickFormat(function(d){ return formatUDM(d, udm) })
            .ticks(10);

        var yAxis = d3.svg.axis()
            .scale(y)
            .orient("left")
            .tickFormat(function(d) { return titleCase(d) })
            .ticks(10);

        var max = d3.max(data, function(d) { return d.Dato })
        var min = d3.min(data, function(d) { return d.Dato })

        y.domain(data.map(function(d) { return d.Regione; }));
        x.domain([min + (min - max) * 5 / 100, max]);

        svg = svg.append("g")
            .attr("transform", "translate(" + margin.left + "," + margin.top + ")")

        svg.append("g")
            .attr("class", "x axis")
            .attr("transform", "translate(0," + height + ")")
            .call(xAxis)
            .selectAll("text")
            .style("text-anchor", "end")
            .attr("dx", "5")
            .attr("dx", "-10")
            .attr("dy", "5")
            .attr("transform", "rotate(-40)" );

        svg.append("g")
            .attr("class", "y axis")
            .call(yAxis)

        // now add titles to the axes
        svg.append("text")
            .attr("class", "x-legend")
            .attr("text-anchor", "middle") // this makes it easy to centre the text as the transform is applied to the anchor
            .attr("transform", "translate(" + (width / 2) + "," + (height - margin.top / 2) + ")") // centre below axis
            .text(data[0].UDM);



        svg.append("text")
            .attr("stroke-width","0.7")
            .attr("stroke","#000")
            .attr("class", "chart-title")
            .attr("text-anchor", "left")
            //.attr("transform", "translate(" + (margin.left+margin.right*2) + "," + (-margin.top/2) + ")") // centre below axis
            .attr("transform", "translate(" + (10) + "," + (0) + ")") // centre below axis
            .text(data[0].Anno)


        var mouseover = function(d) {
            svg.append("text")
                .attr("class", "hover-value")
                .attr("transform", "translate(" + ((x(d.Dato) < width - 30 - d.Dato.toString().length * 3.0) ? (x(d.Dato) + 15) : x(d.Dato) - 30 - formatUDM(d, udm).toString().length * 4.5) + "," +
                    (y(d.Regione) + y.rangeBand() / 1.3) + ")")
                .text(formatUDM(d.Dato, d.UDM))
            d3.select(this).style("fill", color_hover);
        }



        var mouseout = function(d) {
            svg.select("text.hover-value").remove()
            d3.select(this).style("fill", function(d){
                return d3.select(this).classed('selected') ? color_selected : color
            });
        };



        var clicked = function(d) {
            event_listner.regione = d.Regione;
        }



        chart.update = function() {
            data.sort(function(x, y) {
                return d3.descending(x.Dato, y.Dato);
            })



            var max = d3.max(data, function(d) { return d.Dato })
            var min = d3.min(data, function(d) { return d.Dato })

            y.domain(data.map(function(d) { return d.Regione; }));
            x.domain([min + (min - max) * 5 / 100, max]);

            xAxis.tickFormat(function(d){ return formatUDM(d, data[0].UDM) })


            svg.select(".y.axis")
                .transition()
                .duration(1000)
                .call(yAxis)

            svg.select(".x.axis")
                .transition()
                .duration(1000)
                .call(xAxis)
                .selectAll("text")
                .style("text-anchor", "end")
                .attr("dx", "5")
                .attr("dx", "-10")
                .attr("dy", "5")
                .attr("transform", "rotate(-40)" );


            var bars = svg.selectAll('rect').data(data)

            bars.exit()
                .transition()
                .duration(1000)
                .attr("x", 10)
                .attr("width", width - 10)
                .style('fill-opacity', 1e-6)
                .remove();

            bars.enter()
              .append("rect")
                .attr("class", "bar")
                .attr("x", 10)
                .attr("width", width - 10)
                .style("fill", color)
                .on("mouseover", mouseover)
                .on("mouseout", mouseout)
                .on("click", clicked);

            bars
                .transition()
                .duration(1000)
                .attr("y", function(d) { return y(d.Regione); })
                .attr("width", function(d) { return ((x(d.Dato) > 0) ? x(d.Dato) : 0); })
                .attr("x", 10)
                .attr("height", y.rangeBand());


            d3.select('.x-legend').text(data[0].UDM)


/*            svg.selectAll("rect")
                .data(data)
                .transition()
                .duration(1000)
                .attr("id", function(d) { return d.Regione })
                .attr("width", function(d) { return ((x(d.Dato) > 0) ? x(d.Dato) : 0); })
                .attr("x", "1")
                .attr("y", function(d) { return y(d.Regione); })
                .attr("height", y.rangeBand());*/

            svg.select(".chart-title")
                .text(data[0].Anno);

            return chart;
        }


/*

        svg.selectAll(".bar")
            .data(data)
            .enter().append("rect")
            .attr("class", "bar")
            .style("fill", color)
            .attr("id", function(d) { return d.Regione })
            .attr("width", function(d) { return ((x(d.Dato) > 0) ? x(d.Dato) : 0); })
            .attr("y", function(d) { return y(d.Regione); })
            .attr("x", "1")
            .attr("height", y.rangeBand())
            .on("mouseover", mouseover)
            .on("mouseout", mouseout)
            .on("click", clicked);
*/


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
    chart.color_hover = function(_) {
        if (!arguments.length) return color_hover;
        color_hover = _;
        return chart;
    };

    chart.color_selected = function(_) {
        if (!arguments.length) return color_selected;
        color_selected = _;
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

    chart.event_listner = function(_) {
        if (!arguments.length) return event_listner;
        event_listner = _;
        return chart;
    };
    chart.data = function(_) {
        if (!arguments.length) return data;
        data = _;
        return chart;
    };

    return chart
}




function TimeBarChart(selector) {

    var width = $(selector).width(),
        height = 400,
        data = [],
        margin = { top: 60, right: 20, bottom: 20, left: 100 },
        sorting = null,
        x_label = null,
        y_label = null,
        interpolate = false,
        color = 'url(#svgGradient2)',
        color_selected = '#464647',
        color_hover = '#CACACA',
        event_listner = {},
        mouseover,
        mouseout;

    var addGradient = function(svg){

        var defs = svg.append("defs");
        var gradient = defs.append("linearGradient")
            .attr("id", "svgGradient2")
            .attr("x1", "0%")
            .attr("x2", "0%")
            .attr("y1", "100%")
            .attr("y2", "0%");

        gradient.append("stop")
            .attr('class', 'start')
            .attr("offset", "0%")
            .attr("stop-color", "#adefad")
            .attr("stop-opacity", 1);

        gradient.append("stop")
            .attr('class', 'end')
            .attr("offset", "100%")
            .attr("stop-color", "#79e779")
            .attr("stop-opacity", 1);
        }

    var createSVG = function(selector, width, height) {

        var svg = d3.select(selector).append('svg')
            .attr("width", width + margin.left + margin.right)
            .attr("height", height + margin.top + margin.bottom)
          .append("g")
            .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

        svg
          .append("g")
            .attr("class", "x axis")
            .attr("transform", "translate(0," + height + ")")

        svg
          .append("g")
            .attr("class", "y axis")
          .append("text") // just for the title (ticks are automatic)
            .attr("transform", "rotate(-90)") // rotate the text!
            .attr("y", 6)
            .attr("dy", ".71em")
            .style("text-anchor", "end")
            .text(x_label);

        addGradient(svg)

        return svg
    }

    var clicked = function(d){
        event_listner.anno = d.Anno;
    }



    function chart() {

        width = width - margin.left - margin.right,
        height = height - margin.top - margin.bottom;

        var svg = createSVG(selector, width, height);

        var x = d3.scale.ordinal().rangeRoundBands([0, width], .05);
        var y = d3.scale.linear().range([height, 0]);

        var line = d3.svg.line()
        // assign the X function to plot our line as we wish
            .x(function(d) { return x(d.Anno)+x.rangeBand()/2; })
            .y(function(d) { return y(d.Dato);});

        var xAxis = d3.svg.axis()
            .scale(x)
            .orient("bottom")
            .ticks(1);

        var yAxis = d3.svg.axis()
            .scale(y)
            .orient("left")
            .ticks(4)
            .tickFormat(function(d){ return formatUDM(d, udm) });


        svg.append("text")
            .attr("stroke-width","0.7")
            .attr("stroke","#000")
            .attr("class", "chart-title")
            .attr("text-anchor", "bottom")
            //.attr("transform", "translate(" + (margin.left+margin.right*2) + "," + (-margin.top/2) + ")") // centre below axis
            .attr("transform", "translate(" + (18) + "," + (-margin.top*4/5) + ")") // centre below axis
            .text(data[0].Territorio)


        mouseover = function(d) {
                d3.select(this).style('fill', color_hover);
                svg.append("text")
                .attr("class", "hover-value")
                .attr("transform", "translate(" + (x(d.Anno)+(x.rangeBand()/2)-d.Dato.toString().length/2) + "," + (y(d.Dato)-20)+ ")")
                .text(formatUDM(d.Dato, d.UDM))
        }



        mouseout = function(d) {
            d3.select(this).style("fill", color)
            svg.select("text.hover-value").remove()
        }

        chart.update = function() {

            data.sort(function(x, y) {
                return d3.descending(x.Dato, y.Dato);
            });


            var max = d3.max(data, function(d) { return d.Dato })
            var min = d3.min(data, function(d) { return d.Dato })

            min = min - (max-min)/2

            d_anni = data.map(function(d){return d.Anno})

            x.domain(d_anni);
            y.domain([min, max]);

            yAxis.tickFormat(function(d){ return formatUDM(d, data[0].UDM) })

            svg.select(".y.axis")
                .transition()
                .duration(1000)
                .call(yAxis)

            svg.select(".x.axis")
                .transition()
                .duration(1000)
                .call(xAxis)

            var bars = svg.selectAll(".bar").data(data)


            bars.exit()
                .transition()
                .duration(1000)
                .attr("y", y(min))
                .attr("height", height - y(min))
                .style('fill-opacity', 1e-6)
                .remove();

            bars.enter()
              .append("rect")
                .attr("class", "bar")
                .attr("id", function(d){ return "y"+ d.Anno })
                .attr("y", y(min))
                .attr("height", height - y(min))
                .style("fill", color)
                .on("mouseover", mouseover)
                .on("mouseout", mouseout)
                .on("click", clicked);

            bars
                .transition()
                .duration(1000).attr("x", function(d) { return x(d.Anno); })
                .attr("width", x.rangeBand())
                .attr("y", function(d) { return y(d.Dato); })
                .attr("height", function(d) { return ((height - y(d.Dato)-1) >= 0) ? height - y(d.Dato)-1 : 0; });


            if(interpolate){
                var linegraph = svg.selectAll("path.line")
                        .data([data]);

                    linegraph
                        .enter()
                        .append('path')
                        .attr("class", "line")
                        .transition().duration(1000);

                    linegraph
                        .transition()
                        .duration(1000)
                        .ease("linear")
                        .attr("d", line);

            }

            d3.select(".chart-title")
                .text(data[0].Territorio);

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

    chart.color_hover = function(_) {
        if (!arguments.length) return color_hover;
        color_hover = _;
        return chart;
    };

    chart.color_selected = function(_) {
        if (!arguments.length) return color_selected;
        color_selected = _;
        return chart;
    };


    chart.data = function(_) {
        if (!arguments.length) return data;
        data = _;
        return chart;
    };

    chart.udm = function(_) {
        if (!arguments.length) return udm;
        udm = _;
        return chart;
    };

    chart.sorting = function(_) {
        if (!arguments.length) return sorting;
        sorting = _;
        return chart;
    };

    chart.interpolate = function(_) {
        if (!arguments.length) return interpolate;
        interpolate = _;
        return chart;
    };


    chart.mouseout = function(_) {
        if (!arguments.length) return mouseout;
        mouseout = _;
        return chart;
    };


    chart.mouseover = function(_) {
        if (!arguments.length) return mouseover;
        mouseover = _;
        return chart;
    };


    chart.event_listner = function(_) {
        if (!arguments.length) return event_listner;
        event_listner = _;
        return chart;
    };


    return chart
}



function formatUDM(d, udm){
    if(udm.indexOf('percentuali') != -1){
        return it_locale.numberFormat(".2f")(d)+"%"
    }
    else if(udm.indexOf('milioni di euro') != -1){
        return it_locale.numberFormat(",.0f")(d) + " M €"
    }
    else if(udm.indexOf('migliaia di euro') != -1){
        return it_locale.numberFormat(",.0f")(d) + " K €"
    }
    else if(udm.indexOf('euro') != -1){
        return it_locale.numberFormat(",.2f")(d) + " €"
    }
    else if (udm.indexOf('numero') != -1)
        { return it_locale.numberFormat(",")(d) }

    else { return it_locale.numberFormat(",.2f")(d) }
}



function selectYearTimeChart(anno){
    d3.selectAll('#timechart rect').style('fill', 'url(#svgGradient2)');
    d3.selectAll('#timechart rect').classed("selected", false);
    d3.select('#timechart rect#y'+anno).style('fill', '#464647').classed("selected", true)
}

function resetElement(selected_elements, color){
    selected_elements.classed("selected", false);
    selected_elements.style("fill", color);
}
