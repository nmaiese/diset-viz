function ItalyMap(selector){
    var width = $(selector).width(),
    height = width-50,
    centered,
    geo_data = [],
    year = 2015,
    metric = "PIL",
    text_art = false,
    features = [],
    mouseover,
    mouseout,
    clicked;

    var color = d3.scale.linear()
      .clamp(true)
      .range(['white', '#489E2D']);

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

        // Get province name
        function nameFn(d){
          return d && d.properties ? d.properties.name : null;
        }

        // Get province name length
        function nameLength(d){
          var n = nameFn(d);
          return n ? n.length : 0;
        }

        // Get province color
        function fillFn(d){
          //console.log(d.dati.Dato, d.dati.Regione)
          return color(d.dati.Dato)

          //return color(nameLength(d));
        }

        // When clicked, zoom in
        var clicked = function(d) {
          var x, y, k;

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
            .style('fill', function(d){return centered && d===centered ? '#D5708B' : fillFn(d);});

          // Zoom
          g.transition()
            .duration(750)
            .attr('transform', 'translate(' + width / 2 + ',' + height / 2 + ')scale(' + k + ')translate(' + -x + ',' + -y + ')');
        }

        var mouseover = function(d){

          d3.select("#stats-container").style("display", "inline")
          d3.select(this).style('fill', '#262727');
          let region = this.id
          TimeBar.data(myData.filter(function(d){ return d.Regione == region && d.Indicatore == indicatore })).update();

          // Draw effects
          if(text_art){textArt(nameFn(d));}
        }

        var mouseout = function(d){
          // Reset province color
          d3.select("#stats-container").style("display", "none")
          mapLayer.selectAll('path')
            .style('fill', function(d){return centered && d===centered ? '#D5708B' : fillFn(d);});

          // Remove effect text
          effectLayer.selectAll('text').transition()
            .style('opacity', 0)
            .remove();

          // Clear province name
          bigText.text('');
          d3.select("tr#"+d.Regione).style("background-color", "white")
        }

        // Gimmick
        // Just me playing around.
        // You won't need this for a regular map.
        var BASE_FONT = "'Helvetica Neue', Helvetica, Arial, sans-serif";

        var FONTS = [
          "Open Sans",
          "Josefin Slab",
          "Arvo",
          "Lato",
          "Vollkorn",
          "Abril Fatface",
          "Old StandardTT",
          "Droid+Sans",
          "Lobster",
          "Inconsolata",
          "Montserrat",
          "Playfair Display",
          "Karla",
          "Alegreya",
          "Libre Baskerville",
          "Merriweather",
          "Lora",
          "Archivo Narrow",
          "Neuton",
          "Signika",
          "Questrial",
          "Fjalla One",
          "Bitter",
          "Varela Round"
        ];

        function textArt(text){
          // Use random font
          var fontIndex = Math.round(Math.random() * FONTS.length);
          var fontFamily = FONTS[fontIndex] + ', ' + BASE_FONT;

          bigText
            .style('font-family', fontFamily)
            .text(text);

          // Use dummy text to compute actual width of the text
          // getBBox() will return bounding box
          dummyText
            .style('font-family', fontFamily)
            .text(text);
          var bbox = dummyText.node().getBBox();

          var textWidth = bbox.width;
          var textHeight = bbox.height;
          var xGap = 3;
          var yGap = 1;

          // Generate the positions of the text in the background
          var xPtr = 0;
          var yPtr = 0;
          var positions = [];
          var rowCount = 0;
          while(yPtr < height){
            while(xPtr < width){
              var point = {
                text: text,
                index: positions.length,
                x: xPtr,
                y: yPtr
              };
              var dx = point.x - width/2 + textWidth/2;
              var dy = point.y - height/2;
              point.distance = dx*dx + dy*dy;

              positions.push(point);
              xPtr += textWidth + xGap;
            }
            rowCount++;
            xPtr = rowCount%2===0 ? 0 : -textWidth/2;
            xPtr += Math.random() * 10;
            yPtr += textHeight + yGap;
          }

          var selection = effectLayer.selectAll('text')
            .data(positions, function(d){return d.text+'/'+d.index;});

          // Clear old ones
          selection.exit().transition()
            .style('opacity', 0)
            .remove();

          // Create text but set opacity to 0
          selection.enter().append('text')
            .text(function(d){return d.text;})
            .attr('x', function(d){return d.x;})
            .attr('y', function(d){return d.y;})
            .style('font-family', fontFamily)
            .style('fill', '#777')
            .style('opacity', 0);

          selection
            .style('font-family', fontFamily)
            .attr('x', function(d){return d.x;})
            .attr('y', function(d){return d.y;});

          // Create transtion to increase opacity from 0 to 0.1-0.5
          // Add delay based on distance from the center of the <svg> and a bit more randomness.
          selection.transition()
            .delay(function(d){
              return d.distance * 0.01 + Math.random()*1000;
            })
            .style('opacity', function(d){
              return 0.1 + Math.random()*0.4;
            });
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



        max = d3.max(features, function(d){ return d.dati.Dato })
        min = d3.min(features, function(d){ return d.dati.Dato })

        color.domain([min+(min-max)*5/100, max]);


        // Draw each province as a path
        mapLayer.selectAll('path')
          .data(features)
        .enter().append('path')
          .attr('d', path)
          .attr('id', function(d){return d.dati.Regione })
          .attr('vector-effect', 'non-scaling-stroke')
          .style('fill', fillFn)
          .on('mouseover', mouseover)
          .on('mouseout', mouseout)
          .on('click', clicked);

        chart.update = function(){
            max = d3.max(features, function(d){ return d.dati.Dato })
            min = d3.min(features, function(d){ return d.dati.Dato })
            color.domain([min+(min-max)*5/100, max]);
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
    chart.features = function(_) {
        if (!arguments.length) return features;
            features = _;
            return chart;
    };
    chart.geo_data = function(_) {
        if (!arguments.length) return geo_data;
            geo_data = _;
            return chart;
    };
    return chart
}
