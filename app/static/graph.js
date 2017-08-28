// Load map data

var it_IT = {
    "decimal": ",",
    "thousands": ".",
    "grouping": [3],
    "currency": ["€", ""],
    "dateTime": "%a, %e %b %Y - %X",
    "date": "%d/%m/%Y",
    "time": "%H:%M:%S",
    "periods": ["AM", "PM"],
    "days": ["Domenica", "Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato"],
    "shortDays": ["Dom", "Lun", "Mar", "Mer", "Gio", "Ven", "Sab"],
    "months": ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno", "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"],
    "shortMonths": ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu", "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]
}

var it_locale = d3.locale(it_IT);

Array.prototype.unique = function() {
    var a = this.concat();
    for(var i=0; i<a.length; ++i) {
        for(var j=i+1; j<a.length; ++j) {
            if(a[i] === a[j])
                a.splice(j--, 1);
        }
    }

    return a;
};

function getRandomInt(min, max) {
    return Math.floor(Math.random() * (max - min + 1)) + min;
}





function get_dataset_and_map_geo(data, geodata, indicatore, anno){
    data = data.filter(function(d){return (d.Indicatore == indicatore && d.Anno == anno)})
        geodata.forEach(function(d) {
            v = data.filter(function(f) {
                return d.properties.name == f.Regione
            })
        d.dati = v[0]
    })
    return geodata
}

function create_green_select2(selector, item_list, selected, search=true, myclass='myclass'){
    var item_objects = []
    item_list.forEach(function(d, i){ item_objects.push({text: d, id: i}) })
    $(selector).select2({
        data: item_objects,
        containerCssClass: myclass,
        dropdownCssClass: myclass,
    });
    $(selector).select2("val",item_list.indexOf(selected).toString())

    if (!search){ $(selector).select2({minimumResultsForSearch: Infinity}) }

}


function create_green_dropdown(selector, item_list, selected){
    var menu = d3.select(selector);
    menu.append('button')
        .attr('class', 'btn btn-success dropdown-toggle')
        .attr('type', 'button')
        .attr('data-toggle', 'dropdown')
        .html(selected+'<span class="caret"></span>')

    menu.append('ul')
        .attr('class', 'dropdown-menu')
        .selectAll('li')
        .data(item_list)
        .enter()
        .append('li')
        .append('a')
        .text(function(d){return d})
    return menu

}


function formatValue(d, udm){
    if(udm.indexOf('percentuali') != -1){
        return it_locale.numberFormat(".2f")(d.dati.Dato)+"%"
    }
    else if(udm.indexOf('milioni di euro') != -1){
        return it_locale.numberFormat(",.2f")(d.dati.Dato) + " M €"
    }
    else if(udm.indexOf('migliaia di euro') != -1){
        return it_locale.numberFormat(",.2f")(d.dati.Dato) + " K €"
    }
    else if(udm.indexOf('euro') != -1){
        return it_locale.numberFormat(",.2f")(d.dati.Dato) + " €"
    }
    else if (udm.indexOf('numero') != -1)
        { return it_locale.numberFormat(",.0f")(d.dati.Dato) }

    else { return it_locale.numberFormat(",.2f")(d.dati.Dato) }
}





d3.json('static/data/italian-regions.geo.json', function(error, mapData) {
    var ssv = d3.dsv(";", "text/plain");
    ssv('static/data/Assoluti_Regione.csv', function(errorb, data) {

        temi = data.map(function(f){return f.Tema })
        ran = getRandomInt(0, temi.length)
        tema = temi[ran]
        data = data.filter(function(d){ return d.Tema == tema })

        data.forEach(function(d) {
            d['Dato'] = +d['Dato'].replace(',', '.');
            d['Regione'] = d['Territorio'].replace(/'/g, ' ').replace(/ /g, '-').toLowerCase();
            d['Anno'] = +d['Anno']
            d['Indicatore'] = d['Indicatore'].replace(/"/g,  "'")
        })


        indicatori = data.map(function(f){return f.Indicatore }).unique()
        indicatore = indicatori[getRandomInt(0, indicatori.length-1)]
        anni = data.filter(function(d){ return d.Indicatore ==  indicatore}).map(function(f){return f.Anno }).unique()
        anno = anni[getRandomInt(0, anni.length-1)]
        features = mapData.features;
        features.forEach(function(d) {
            d.properties.name = d.properties.name.replace(/ /g, '-')
        })



        var header_list = Object.keys(data[0])



        function DrawTable(selector, features, year, metric) {


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



        myData = data;


        var dataset = get_dataset_and_map_geo(data, features, indicatore, anno)
        var fonte = dataset[0].dati.Fonte
        var udm = dataset[0].dati.UDM
        var archivio = dataset[0].dati.Archivio
        d3.select("span#fonte").text(fonte)
        d3.select("span#udm").text(udm)
        d3.select("span#archivio").text(archivio)

        console.log(anno, indicatore, fonte, udm, archivio)

        Italy = ItalyMap('#map').features(dataset);
        Italy();
        Bar = BarChart('#barchart').data(dataset)
        Bar()
        var TimeBar = TimeBarChart('#timechart').data(data.filter(function(d){ return d.Regione == 'piemonte' && d.Indicatore == indicatore })).height(200)
        TimeBar();

        $(function() {



/*            <div class="dropdown" id="metric-dropdown">
              Indicatore:
              <button class="btn btn-success dropdown-toggle" type="button" data-toggle="dropdown">
              Reddito Primario
              <span class="caret"></span></button>
              <ul class="dropdown-menu">
                <li><a>Reddito Primario</a></li>
                <li><a>Reddito disponibile</a></li>
                <li><a>Distribuzione secondaria</a></li>
                <li><a>PIL</a></li>
                <li><a>PIL per abitante</a></li>
              </ul>
            </div>*/

            //var menu_indicatori = create_green_dropdown('#metric-dropdown', indicatori, indicatore);

            $('#indicatore').text(tema)


            create_green_select2('#metric-dropdown', indicatori, indicatore, search=true, myclass='metric');
            create_green_select2('#year-dropdown', anni, anno, search=false, myclass='year');

            $("#metric-dropdown").on("select2:select", function (e) {
                indicatore = e.params.data.text
                var anni = data.filter(function(d){ return d.Indicatore ==  indicatore }).map(function(f){return f.Anno }).unique();
                var anno = anni[getRandomInt(0, anni.length-1)];
                var dataset = get_dataset_and_map_geo(data, features, indicatore, anno)
                var filtered = data.filter(function(d){ return d.Regione == 'piemonte' && d.Indicatore == indicatore })
                var fonte = dataset[0].dati.Fonte
                var udm = dataset[0].dati.UDM
                var archivio = dataset[0].dati.Archivio
                d3.select("span#fonte").text(fonte)
                d3.select("span#udm").text(udm)
                d3.select("span#archivio").text(archivio)


                Italy.features(dataset).update();
                create_green_select2('#year-dropdown', anni, anno);
                $("#label").html(indicatore + " <i>"+anno+"</i>");
                Bar.data(dataset).update();
                TimeBar.data(filtered).update();
            });

            $("#year-dropdown").on("select2:select", function (e) {
                var anno = e.params.data.text
                var dataset = get_dataset_and_map_geo(data, features, indicatore, anno)
                var fonte = dataset[0].dati.Fonte
                var udm = dataset[0].dati.UDM
                var archivio = dataset[0].dati.Archivio
                d3.select("span#fonte").text(fonte)
                d3.select("span#udm").text(udm)
                d3.select("span#archivio").text(archivio)

                Italy.features(dataset).update();
                Bar.data(dataset).update();
                $("#label").html(indicatore + " <i>"+anno+"</i>");

            });
            $('#play').on('click', function(d) {
                $("#play").html("<i class='fa fa-space-shuttle faa-passing animated'></i>")
                var anni = data.filter(function(d){ return d.Indicatore ==  indicatore }).map(function(f){return f.Anno }).unique();
                var year = anni[0];
                var playInterval = setInterval(function() {
                    if (year == anni[anni.length-1]) {
                        clearInterval(playInterval)
                        $("#play").html("<span class='glyphicon glyphicon-play-circle'></span> Play")

                    }
                    var dataset = get_dataset_and_map_geo(data, features, indicatore, year)
                    Italy.features(dataset).update();
                    Bar.data(dataset).update();
                    create_green_select2('#year-dropdown', anni, year);
                    $("#label").html(indicatore + " <i>"+year+"</i>");
                    year++
                }, 2000);
            })


        });
    })
})
