var myX
var myY
var myDomain

function BarChart(selector) {
    var width = $(selector).width(),
        height = 600,
        centered,
        year = 2015,
        metric = "PIL",
        text_art = false,
        data = [],
        mouseover,
        mouseout,
        clicked,
        margin = { top: 10, right: 10, bottom: 73, left: 100 };



    var createSVG = function(selector) {
        var svg = d3.select(selector).append('svg')
            .attr('width', width)
            .attr('height', height)
        return svg
    }

    function chart() {

        var svg = createSVG(selector);
        var udm = data[0].dati.UDM;

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
            return d3.descending(x.dati.Dato, y.dati.Dato);
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

        var max = d3.max(features, function(d) { return d.dati.Dato })
        var min = d3.min(features, function(d) { return d.dati.Dato })

        y.domain(data.map(function(d) { return d.dati.Regione; }));
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
            .text(data[0].dati.UDM);




        mouseover = function(d) {
            d3.select("path#" + d.dati.Regione).style("fill", "#FF5B5B");
            svg.append("line")
                .attr("class", "grid-line")
                .attr("x1", x(d.dati.Dato) - 1)
                .attr("y1", y(d.dati.Regione) + y.rangeBand())
                .attr("x2", x(d.dati.Dato) - 1)
                .attr("y2", height)
                .attr("style", "stroke:#50d750;stroke-width:1");

            svg.append("text")
                .attr("class", "hover-value")
                .attr("transform", "translate(" + ((x(d.dati.Dato) < width - 30 - d.dati.Dato.toString().length * 3.0) ? (x(d.dati.Dato) + 10) : x(d.dati.Dato) - 30 - formatValue(d, udm).toString().length * 4.5) + "," +
                    (y(d.dati.Regione) + y.rangeBand() / 1.4) + ")")
                .text(formatValue(d, udm))
        }


        var mouseout = function(d) {
            d3.selectAll("line").remove()
            d3.selectAll("text.hover-value").remove()
            d3.select("path#" + d.dati.Regione).style("fill", function(d) { return Italy.color()(d.dati.Dato) });
        }

        chart.update = function() {
            data.sort(function(x, y) {
                return d3.descending(x.dati.Dato, y.dati.Dato);
            })


            var max = d3.max(features, function(d) { return d.dati.Dato })
            var min = d3.min(features, function(d) { return d.dati.Dato })



            y.domain(data.map(function(d) { return d.dati.Regione; }));
            x.domain([min + (min - max) * 5 / 100, max]);

            xAxis.tickFormat(function(d){ return formatUDM(d, features[0].dati.UDM) })

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


            svg.selectAll("rect")
                .data(data)
                .transition()
                .duration(1000)
                .attr("width", function(d) { return ((x(d.dati.Dato) > 0) ? x(d.dati.Dato) : 0); })
                .attr("x", "1")
                .attr("y", function(d) { return y(d.dati.Regione); })
                .attr("height", y.rangeBand());

            d3.select('.x-legend').text(data[0].dati.UDM)

            return chart;
        }


        svg.selectAll(".bar")
            .data(data)
            .enter().append("rect")
            .attr("class", "bar")
            .style("fill", "url(#svgGradient)")
            .attr("id", function(d) { return d.Regione })
            .attr("width", function(d) { return ((x(d.dati.Dato) > 0) ? x(d.dati.Dato) : 0); })
            .attr("y", function(d) { return y(d.dati.Regione); })
            .attr("x", "1")
            .attr("height", y.rangeBand())
            .on("mouseover", mouseover)
            .on("mouseout", mouseout);

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



function TimeBarChart(selector) {
    var width = $(selector).width(),
        height = 400,
        data = [],
        margin = { top: 30, right: 20, bottom: 20, left: 100 };


    var createSVG = function(selector) {
        var svg = d3.select(selector).append('svg')
            .attr('width', width)
            .attr('height', height)
        return svg
    }

    function chart() {

        var udm = data[0].UDM;
        var svg = createSVG(selector);
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


        data.sort(function(x, y) {
            return d3.ascending(x.Anno, y.Anno);
        })


        width = +svg.attr("width") - margin.left - margin.right,
            height = +svg.attr("height") - margin.top - margin.bottom;

        var x = d3.scale.ordinal().rangeRoundBands([0, width], .05);
        var y = d3.scale.linear().range([height, 0]);


        var line = d3.svg.line()
        // assign the X function to plot our line as we wish
        .x(function(d) {
            return x(d.Anno)+x.rangeBand()/2;
        })
        .y(function(d) {
            return y(d.Dato);
        });

        var xAxis = d3.svg.axis()
            .scale(x)
            .orient("bottom")
            .ticks(1);

        var yAxis = d3.svg.axis()
            .scale(y)
            .orient("left")
            .ticks(4)
            .tickFormat(function(d){ return formatUDM(d, udm) });

        var max = d3.max(data, function(d) { return d.Dato })
        var min = d3.min(data, function(d) { return d.Dato })
        min = min - (max-min)/2

        x.domain(data.map(function(d) { return d.Anno; }));
        y.domain([min + (min - max) * 5 / 100, max]);

        var container = svg

        svg = svg.append("g")
            .attr("transform", "translate(" + margin.left + "," + margin.top + ")")

        svg.append("g")
            .attr("class", "x axis")
            .attr("transform", "translate(0," + height + ")")
            .call(xAxis)
            .selectAll("text")
            .style("text-anchor", "end")
            .attr("dx", "5");

        svg.append("g")
            .attr("class", "y axis")
            .call(yAxis)

        // now add titles to the axes

        // svg.append("text")
        //     .attr("class", "x-legend")
        //     .attr("y",(20 - margin.left))
        //     .attr("x",0 - (height / 2))
        //     .attr("text-anchor", "middle") // this makes it easy to centre the text as the transform is applied to the anchor
        //     .attr("transform", "rotate(-90)" )
        //     .text(data[0].UDM);



        mouseover = function(d) {
            d3.select(this).style('fill', '#464647');
        }


        var mouseout = function(d) {
            d3.select(this).style("fill", "url(#svgGradient2)")
        }

        chart.update = function() {

            data.sort(function(x, y) {
                return d3.ascending(x.Anno, y.Anno);
            })

            var max = d3.max(data, function(d) { return d.Dato })
            var min = d3.min(data, function(d) { return d.Dato })
            min = min - (max-min)/2

            d_anni = data.map(function(d){return d.Anno})

            x.domain(d_anni);
            y.domain([min + (min - max) * 5 / 100, max]);

            yAxis.tickFormat(function(d){ return formatUDM(d, data[0].UDM) })
            //xAxis.scale(x)

            svg.select(".y.axis")
                .transition()
                .duration(1000)
                .call(yAxis)



            svg.select(".x.axis")
                .transition()
                .duration(1000)
                .call(xAxis)

/*            let bars = svg.selectAll("rect")
            console.log(bars[0].length , x.domain().length)
            if (bars[0].length > x.domain().length){
                for(i = 0; i < bars[0].length-x.domain().length; i++){
                    svg.select("g.bars rect").remove()
                }
            }
            else if(bars[0].length < x.domain().length){
                for(i = 0; i < x.domain().length-bars[0].length; i++){
                    svg.select("g.bars").append("rect")
                    .style("fill", "url(#svgGradient2)")
                    .on("mouseover", mouseover)
                    .on("mouseout", mouseout);


                }
            }
*/
            svg.selectAll("rect").data(data, function(d){return (d.Anno)})
                .transition()
                .duration(1000)
                .attr("class", "bar")
                .style("fill", "url(#svgGradient2)")
                .attr("id", function(d) { return 'y'+d.Anno })
                .attr("x", function(d) { console.log(d.Anno); return x(d.Anno); })
                .attr("width", x.rangeBand())
                .attr("y", function(d) { return ((y(d.Dato)>0) ? y(d.Dato) : 0); })
                .attr("height", function(d) { return ((height - y(d.Dato) > 0) ? height - y(d.Dato)- 1 : 0); });


            svg.selectAll('path.data-line')
                .transition()
                .duration(1000)
                .attr("d", line(data));


            d3.select(".chart-title")
                .text(data[0].Territorio);


            return chart;
        }


        svg
        .append("g").attr("class", "bars").selectAll(".bar")
            .data(data)
            .enter().append("rect")
            .attr("class", "bar")
            .style("fill", "url(#svgGradient2)")
            .attr("id", function(d) { return 'y'+d.Anno })
            .attr("x", function(d) { console.log(d.Anno); return x(d.Anno); })
            .attr("width", x.rangeBand())
            .attr("y", function(d) { return ((y(d.Dato)>0) ? y(d.Dato) : 0); })
            .attr("height", function(d) { return ((height - y(d.Dato) > 0) ? height - y(d.Dato)- 1 : 0); })
            .on("mouseover", mouseover)
            .on("mouseout", mouseout);

        svg.append('path')
            .attr('class', 'data-line')
            .style('opacity', 0.9)
            .attr("d", line(data));


        container.append("text")
            .attr("stroke-width","0.7")
            .attr("stroke","#000")
            .attr("class", "chart-title")
            .attr("text-anchor", "middle")
            .attr("transform", "translate(" + ((margin.left*2+width) / 2) + "," + (15) + ")") // centre below axis

            .text(data[0].Territorio);



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
    chart.data = function(_) {
        if (!arguments.length) return data;
        data = _;
        return chart;
    };

    return chart
}




function formatUDM(d, udm){
    if(udm.indexOf('percentuali') != -1){
        return it_locale.numberFormat(".2f")(d)+"%"
    }
    else if(udm.indexOf('milioni di euro') != -1){
        return it_locale.numberFormat(",")(d) + " M €"
    }
    else if(udm.indexOf('migliaia di euro') != -1){
        return it_locale.numberFormat(",")(d) + " K €"
    }
    else if(udm.indexOf('euro') != -1){
        return it_locale.numberFormat(",.2f")(d) + " €"
    }
    else if (udm.indexOf('numero') != -1)
        { return it_locale.numberFormat(",")(d) }

    else { return it_locale.numberFormat(",.2f")(d) }
}
