function ItalyMap(selector){
    var width = $(selector).width(),
    height = width-50,
    centered,
    year = 2015,
    metric = "PIL",
    text_art = false,
    data = [],
    indicatore,
    tema,
    anno,
    mouseover,
    mouseout,
    clicked,
    event_listner;

    var color = d3.scale.linear()
      .clamp(true)
      .range(['red', 'white', '#489E2D']);

    var projection = d3.geo.mercator()
      .scale(3.6*width)
      // Center the Map in Italy
      .center([13,42])
      .translate([width / 2, height / 2]);

    var path = d3.geo.path()
      .projection(projection);


    var createSVG = function(selector){

        var svg = d3.select(selector).append('svg')
          .attr('width', width)
          .attr('height', height);

        // Add background
        svg.append('rect')
          .attr('class', 'background')
          .attr('width', width)
          .attr('height', height)
          .on('click', clicked);

        return svg
    }

    function chart(){

        function nameFn(d){
          return d && d.properties ? d.properties.name : null;
        }

        function nameLength(d){
          var n = nameFn(d);
          return n ? n.length : 0;
        }

        function fillFn(d){
          return color(d.Dato)
        }

        // When clicked, zoom in
        var clicked = function(d) {
/*          var x, y, k;

          // Compute centroid of the selected path
          if (d && centered !== d) {
            var centroid = path.centroid(d);
            x = centroid[0];
            y = centroid[1];
            k = 4;
            centered = d;
          } else {
            x = width / 2;
            y = height / 2;
            k = 1;
            centered = null;
          }

          // Highlight the clicked province
          mapLayer.selectAll('path')
            .style('fill', function(d){return centered && d===centered ? '#464647' : fillFn(d);});

          // Zoom
          g.transition()
            .duration(750)
            .attr('transform', 'translate(' + width / 2 + ',' + height / 2 + ')scale(' + k + ')translate(' + -x + ',' + -y + ')');
*/
          event_listner.regione = this.id;
        }

        var mouseover = function(d){

          d3.select(this).style('fill', '#cacaca');
          var regione = this.id
          //TimeBar.data(myData.filter(function(d){ return d.Regione == regione && d.Indicatore == indicatore })).update();
        }


        var mouseout = function(d){
          mapLayer.selectAll('path')
            .style('fill', function(d){return centered && d===centered ? '#464647' : fillFn(d);});
        }


        // Set svg width & height

        var svg = createSVG(selector);

        var g = svg.append('g');

        var effectLayer = g.append('g')
          .classed('effect-layer', true);

        var mapLayer = g.append('g')
          .classed('map-layer', true);

        var dummyText = g.append('text')
          .classed('dummy-text', true)
          .attr('x', 10)
          .attr('y', 30)
          .style('opacity', 0);

        var bigText = g.append('text')
          .classed('big-text', true)
          .attr('x', 20)
          .attr('y', 45);



        var max = d3.max(data, function(d){ return d.Dato })
        var min = d3.min(data, function(d){ return d.Dato })
        var avg = d3.sum(data, function(d){ return d.Dato })/data.length

        color.domain([min, avg ,max]);


        // Draw each province as a path
        mapLayer.selectAll('path')
          .data(data)
        .enter().append('path')
          .attr('d', path)
          .attr('id', function(d){return d.properties.name })
          .attr('vector-effect', 'non-scaling-stroke')
          .style('fill', fillFn)
          .on('mouseover', mouseover)
          .on('mouseout', mouseout)
          .on('click', clicked);

        chart.update = function(){
            var max = d3.max(data, function(d){ return d.Dato })
            var min = d3.min(data, function(d){ return d.Dato })
            var avg = d3.sum(data, function(d){ return d.Dato })/data.length

            color.domain([min+(min-max)*5/100,avg, max]);
            mapLayer.selectAll('path')
                 .transition()
                 .duration(1000)
                .style('fill', fillFn);
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
    chart.anno = function(_) {
      if (!arguments.length) return anno;
        anno = _;
        return chart;
    };

    chart.indicatore = function(_) {
        if (!arguments.length) return indicatore;
            indicatore = _;
            return chart;
    };
    chart.event_listner = function(_) {
      if (!arguments.length) return event_listner;
        event_listner = _;
        return chart;
    };
    return chart
}
