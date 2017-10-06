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



function replace_missing_value(data, regione){
    if (data.map(function(d){return d.Regione }).indexOf(regione)==-1){
        var missing = Object();
        Object.assign(missing, data[0]);
        missing.Regione  = regione;
        missing.Dato = null;
        data.push(missing)
    }
    return data
}


function getRandomInt(min, max) {
    return Math.floor(Math.random() * (max - min + 1)) + min;
}

function getRandomValue(items){
    return items[getRandomInt(0, items.length-1)];
}

function get_dataset_and_map_geo(data, geodata, indicatore, anno){
    data = data.filter(function(d){return (d.Indicatore == indicatore && d.Anno == anno)})
    geodata.forEach(function(d) {
        data = replace_missing_value(data, d.properties.name)
        v = data.filter(function(f) { return d.properties.name == f.Regione })
        d.dati = v[0]
    })
    return geodata
}

function delete_green_select2(selector){
    $(selector).select2("destroy");
    d3.selectAll(selector+" option").remove()
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



function formatData(data){

    data.forEach(function(d) {
        d['Dato'] = +d['Dato'].replace(',', '.');
        d['Regione'] = d['Territorio'].replace(/'/g, ' ').replace(/ /g, '-').toLowerCase();
        d['Anno'] = +d['Anno']
        d['Indicatore'] = d['Indicatore'].replace(/"/g,  "'")
    })

    return data

}

function selectDataset(data, tema=false, indicatore=false, anno=false, regione=false){
    data = ((tema) ? data.filter(function(d){return d.Tema == tema}) : data)
    data = ((indicatore) ? data.filter(function(d){return d.Indicatore == indicatore}) : data)
    data = ((anno) ? data.filter(function(d){return d.Anno == anno}) : data)
    data = ((regione) ? data.filter(function(d){return d.Regione == regione}) : data)
    return data
}



function getRandomParams(data, tema=null, indicatore=null, regione=null, anno=null){

    var regioni = d3.set(data.map(function(f){return f.Regione })).values()
    regione = ((!regione) ? getRandomValue(regioni) : regione)

    var temi = d3.set(data.map(function(f){return f.Tema })).values()
    tema = ((!tema) ? getRandomValue(temi) : tema)

    data = selectDataset(data, tema=tema)
    var indicatori = d3.set(data.map(function(f){return f.Indicatore })).values()

    indicatore = ((!indicatore) ? getRandomValue(indicatori) : indicatore)

    data = selectDataset(data, false, indicatore)

    var anni = d3.set(data.map(function(f){return f.Anno })).values()
    anno = ((!anno) ? getRandomValue(anni) : anno)

    console.log(indicatore, anno, tema, regione)
    return { 'tema': tema, 'temi':temi, 'indicatore': indicatore,
            'anno': anno, 'regione': regione, 'regioni': regioni,
            'indicatori': indicatori, 'anni':anni };
}

function updateInfo(data){
    var fonte = data[0].dati.Fonte
    var udm = data[0].dati.UDM
    var archivio = data[0].dati.Archivio

    d3.select("span#fonte").text(fonte)
    d3.select("span#udm").text(udm)
    d3.select("span#archivio").text(archivio)
}

d3.json('static/data/italian-regions.geo.json', function(error, mapData) {
    var ssv = d3.dsv(";", "text/plain");
    ssv('static/data/Assoluti_Regione.csv', function(errorb, data) {

        data = formatData(data);

        var params = getRandomParams(data);
        features = mapData.features;

        var temi = params.temi;
        var tema = params.tema;
        var indicatore = params.indicatore;
        var indicatori = params.indicatori;
        var anni = params.anni;
        var anno = params.anno;
        var regioni = params.regioni;
        var regione = params.regione;


        features.forEach(function(d) {
            d.properties.name = d.properties.name.replace(/ /g, '-')
        })

        myData = data;

        var dataset = get_dataset_and_map_geo(data, features, indicatore, anno)
        var dataset_regione = data.filter(function(d){ return d.Regione == regione && d.Indicatore == indicatore })

        updateInfo(dataset);

        Italy = new ItalyMap('#map').features(dataset).indicatore(indicatore);
        Bar = new BarChart('#barchart').data(dataset).height(400);
        TimeBar = new TimeBarChart('#timechart')
            .data(dataset_regione)
            .height(200)
            .interpolate(true);

        Italy();
        Bar();
        TimeBar().update();

        selectYearTimeChart(anno);

        $(function() {

            $('#indicatore').text(tema);

            create_green_select2('#metric-dropdown', indicatori, indicatore, search=true, myclass='metric');
            create_green_select2('#year-dropdown', anni, anno, search=false, myclass='year');

            $("#metric-dropdown").on("select2:select", function (e) {

                var indicatore = e.params.data.text;
                var params = getRandomParams(data, tema=tema, indicatore=indicatore);
                var map_dataset = get_dataset_and_map_geo(data, features, indicatore, params.anno)
                var filtered = selectDataset(data,
                                            tema=params.tema,
                                            indicatore=params.indicatore,
                                            anno=false,
                                            regione=params.regione);

                updateInfo(map_dataset);
                Italy.features(map_dataset).update();
                delete_green_select2('#year-dropdown');
                create_green_select2('#year-dropdown', params.anni, params.anno);
                $("#label").html(indicatore + " <i>"+anno+"</i>");
                Bar.data(map_dataset).update();
                TimeBar.data(filtered).update();
                selectYearTimeChart(params.anno);

            });

            $("#year-dropdown").on("select2:select", function (e) {
                var anno = e.params.data.text
                var  map_dataset = get_dataset_and_map_geo(data, features, indicatore, anno)
                updateInfo(map_dataset);

                Italy.features(map_dataset).update();
                Bar.data(map_dataset).update();

                selectYearTimeChart(anno)
                $("#label").html(indicatore + " <i>"+anno+"</i>");

            });
            $('#play').on('click', function(d) {

                function playYear(year){
                    if (year == anni[anni.length-1]) {
                        clearInterval(playInterval)
                        $("#play").html("<span class='glyphicon glyphicon-play-circle'></span> Play")

                    }
                    d3.selectAll('#timechart rect').style('fill', 'url(#svgGradient2)');
                    d3.select('#timechart rect#y'+year).style('fill', '#464647')

                    var dataset = get_dataset_and_map_geo(data, features, indicatore, year)
                    Italy.features(dataset).update();

                    Bar.data(dataset).update();
                    create_green_select2('#year-dropdown', anni, year);
                    $("#label").html(indicatore + " <i>"+year+"</i>");
                    year++
                    return year

                }
                $("#play").html("<i class='fa fa-space-shuttle faa-passing animated'></i>")
                var anni = data.filter(function(d){ return d.Indicatore ==  indicatore }).map(function(f){return f.Anno }).unique();
                var year = anni[0];
                year = playYear(year);
                var playInterval = setInterval(function() {
                    year = playYear(year);
                }, 2000);
            })


        });
        console.timeEnd('Plot #3')
    })
})


