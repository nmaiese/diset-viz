// Load map data
d3.json('/static/data/italian-regions.geo.json', function(error, mapData) {
    var ssv = d3.dsv(";", "text/plain");
    ssv('/static/data/istat-reddito-regioni.csv', function(errorb, data) {


        data.forEach(function(d) {
            d['Distribuzione secondaria'] = +d['Distribuzione secondaria'].replace(',', '.');
            d['PIL'] = +d['PIL'].replace(',', '.');
            d['PIL per abitante'] = +d['PIL per abitante'].replace(',', '.');
            d['Reddito Primario'] = +d['Reddito Primario'].replace(',', '.');
            d['Reddito disponibile'] = +d['Reddito disponibile'].replace(',', '.');
            d['Regione'] = d['Regione'].toLowerCase();
        })


        features = mapData.features;
        stat_data = data

        features.forEach(function(d) {
            v = data.filter(function(f) {
                return d.properties.name == f.Regione
            })

            d.region = d.properties.name.replace(/ /g, '-')
            v.forEach(function(f) { d[f.Anno] = f })
        })

        function DrawTable(selector, features, year, metric) {

            var header_list = ['Regione', 'Reddito Primario', 'Reddito disponibile', 'Distribuzione secondaria', 'PIL', 'PIL per abitante']

            var table = d3.select(selector).append('table').attr('class', 'table table-bordered table-hover').attr("id", "data-table");
            var thead = table.append('thead').append('tr');
            thead.append('th').text('#')
            thead.append('th').text('Regione')
            thead.append('th').text('Reddito Primario')
            thead.append('th').text('Reddito disponibile')
            thead.append('th').text('Distribuzione secondaria')
            thead.append('th').text('PIL')
            thead.append('th').text('PIL per abitante')

            var tbody = table.append('tbody')
            var tablerow = tbody.selectAll("tr").data(features).enter().append("tr").attr("id", function(d) { return d.region })

            tablerow.append("td");
            tablerow.append("td").text(function(d) { return titleCase(d.region) })
            tablerow.append("td").text(function(d) { return d[year]['Reddito Primario'] })
            tablerow.append("td").text(function(d) { return d[year]['Reddito disponibile'] })
            tablerow.append("td").text(function(d) { return d[year]['Distribuzione secondaria'] })
            tablerow.append("td").text(function(d) { return d[year]['PIL'] })
            tablerow.append("td").text(function(d) { return d[year]['PIL per abitante'] })

            var dataTable = $('#data-table').DataTable({
                paging: false,
                searching: false,
                order: [
                    [header_list.indexOf(metric) + 1, 'desc']
                ]
            });


            dataTable.on('order.dt search.dt', function() {
                dataTable.column(0, { search: 'applied', order: 'applied' }).nodes().each(function(cell, i) {
                    cell.innerHTML = i + 1;
                });
            }).draw();

            return table
        }

        var mapRegions = features.map(function(d) { return d.properties.name })
        var dataRegions = d3.map(data, function(d) { return d.Regione; }).keys()

        var year = 2015
        var metric = 'Reddito Primario'

        Italy = ItalyMap('#map').features(features).year(year).metric(metric);
        Italy();
        Bar = BarChart('#barchart').data(features).year(year).metric(metric)
        Bar();

        bTable = DrawTable("#stats-table", features, year, metric)

        $(function() {
            $('#metric-dropdown li').on('click', function(d) {
                Italy.metric(d.target.text).update();
                Bar.metric(d.target.text).update();
                metric = d.target.text
                var btn = $('#metric-dropdown button').html(d.target.text + " <span class='caret'></span>")
                $("#label").html(metric + " <i>"+year+"</i>");
                $("#stats-table #data-table_wrapper").remove();
                bTable = DrawTable("#stats-table", features, year, d.target.text);
            });


            $('#year-dropdown li').on('click', function(d) {
                Italy.year(+d.target.text).update();
                Bar.year(+d.target.text).update();
                year = +d.target.text
                var btn = $('#year-dropdown button').html(d.target.text + " <span class='caret'></span>")
                $("#label").html(metric + " <i>"+year+"</i>");
                $("#stats-table #data-table_wrapper").remove();
                bTable = DrawTable("#stats-table", features, +d.target.text, metric)
            });

            $('#play').on('click', function(d) {
                var year = 2011;
                var playInterval = setInterval(function() {
                    if (year == 2015) { clearInterval(playInterval) }
                    console.log(year)
                    Italy.year(year).update()
                    Bar.year(year).update();
                    $("#label").html(metric + " <i>"+year+"</i>");
                    $("#stats-table #data-table_wrapper").remove();
                    bTable = DrawTable("#stats-table", features, year, metric)
                    var btn = $('#year-dropdown button').html(year + " <span class='caret'></span>")
                    year++
                }, 2000);
            })
        });
    })
})
