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

    return { 'tema': tema, 'temi':temi, 'indicatore': indicatore,
            'anno': anno, 'regione': regione, 'regioni': regioni,
            'indicatori': indicatori, 'anni':anni };
}

function updateInfo(data){
    var fonte = data[0].Fonte
    var udm = data[0].UDM
    var archivio = data[0].Archivio

    d3.select("span#fonte").text(fonte)
    d3.select("span#udm").text(udm)
    d3.select("span#archivio").text(archivio)
}

d3.json('static/data/italian-regions.geo.json', function(error, map_data) {
    var ssv = d3.dsv(";", "text/plain");
    ssv('static/data/Assoluti_Regione.csv', function(errorb, data) {

        data = format_data(data);
        map_data = format_geo_data(map_data);

        params = getRandomParams(data);

        var data_subset = get_data_subset(data, params);
        var data_charts = get_data_for_chart(data_subset, map_data, params);

        Data = data_charts;
        Geo = map_data;

        Charts = init_chart(data_charts.year, data_charts.region, data_charts.map, params);
        my_lst = add_filter_event_listner(Charts, data_subset, map_data, params);

        updateInfo(data_charts.region);

        $(function() {

            $('#indicatore').text(params.tema);

            function apply_dropown(){
                var data_subset = get_data_subset(data, params);
                var data_charts = get_data_for_chart(data_subset, map_data, params);
                var my_lst = add_filter_event_listner(Charts, data_subset, map_data, params);
                update_charts(data_charts, Charts.Italy, Charts.RegionChart, Charts.YearChart);
                updateInfo(data_charts.region);
            }

            create_green_select2('#tema-dropdown', params.temi, params.tema, search=true, myclass='metric');
            create_green_select2('#metric-dropdown', params.indicatori, params.indicatore, search=true, myclass='metric');
            create_green_select2('#year-dropdown', params.anni, params.anno, search=false, myclass='year');

            $("#tema-dropdown").on("select2:select", function (e) {
                var tema = e.params.data.text;
                console.log(params.tema, tema)
                params = getRandomParams(data, tema=tema, indicatore=null, regione=params.regione);
                console.log(params.tema)
                delete_green_select2('#metric-dropdown');

                create_green_select2('#metric-dropdown', params.indicatori, params.indicatore, search=true, myclass='metric');

                apply_dropown();
            });

            $("#metric-dropdown").on("select2:select", function (e) {

                var indicatore = e.params.data.text;
                params = getRandomParams(data, tema=params.tema, indicatore=indicatore, regione=params.regione);

                delete_green_select2('#year-dropdown');
                create_green_select2('#year-dropdown', params.anni, params.anno);

                apply_dropown();

            });

            $("#year-dropdown").on("select2:select", function (e) {
                var anno = e.params.data.text
                params = getRandomParams(data, tema=params.tema, indicatore=params.indicatore, regione=params.regione, anno=anno);
                apply_dropown();
            });



            $('#play').on('click', function(d) {

                function showDataOverYear(year){
                    if (year == params.anni[params.anni.length-1]) {
                        clearInterval(playInterval)
                        $("#play").html("<span class='glyphicon glyphicon-play-circle'></span> Play").removeAttr("disabled");
                    }
                    my_lst.anno = year;
                    create_green_select2('#year-dropdown', params.anni, year.toString());
                    year++
                    return year
                }

                $("#play").html("<i class='fa fa-space-shuttle faa-passing animated'></i>").attr('disabled', 'disabled')
                var year = params.anni[0];
                year = showDataOverYear(year);
                var playInterval = setInterval(function() {
                    year = showDataOverYear(year);
                }, 2000);
            })
        });
    })
})


