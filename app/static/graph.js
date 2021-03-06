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


function titleCase(str) {
     str = str.replace(/-/g, ' ')
     if(str=="valle d aosta"){
      return "Valle d'Aosta"
     }
     else{
       str = str.toLowerCase().split(' ');
       for(var i = 0; i < str.length; i++){
            str[i] = str[i].split('');
            str[i][0] = str[i][0].toUpperCase();
            str[i] = str[i].join('');
       }
       return str.join(' ');
     }
}





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
    $(selector).val(item_list.indexOf(selected)).trigger("change");

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


function getRandomParams(data, tema=null, indicatore=null, regione=null, anno=null){

    var temi = d3.set(data.map(function(f){return f.Tema })).values()
    tema = ((!tema) ? getRandomValue(temi) : tema)

    var filtred_data = data.filter(function(f){return f.Tema == tema; })

    var indicatori = d3.set(filtred_data.map(function(f){return f.Indicatore })).values()
    indicatore = ((!indicatore) ? getRandomValue(indicatori) : indicatore)

    filtred_data = data.filter(function(f){return f.Tema == tema && f.Indicatore == indicatore; })

    var regioni = d3.set(filtred_data.map(function(f){return f.Regione })).values()
    regione = ((!regione) ? getRandomValue(regioni) : regione)

    var anni = d3.set(filtred_data.map(function(f){return f.Anno })).values()
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

function draw_charts(map_data, data){

        data = format_data(data);
        map_data = format_geo_data(map_data);

        params = getRandomParams(data);

        var data_subset = get_data_subset(data, params);
        var data_charts = get_data_for_chart(data_subset, map_data, params);

        myData = data;
        Data = data_charts;
        Geo = map_data;

        Charts = init_chart(data_charts.year, data_charts.region, data_charts.map, params);
        my_lst = add_filter_event_listner(Charts, data_subset, map_data, params);

        updateInfo(data_charts.region);

        $(function() {

            // $('#play').on('click', function(d) {

            //     function showDataOverYear(index, anni){
            //         if (index == anni.length-1) {
            //             clearInterval(playInterval)
            //             $("#play").html("<span class='glyphicon glyphicon-play-circle'></span> Play").removeAttr("disabled");
            //             $('#random').removeAttr('disabled');
            //             $('#year-dropdown').removeAttr('disabled');
            //             $('#metric-dropdown').removeAttr('disabled');
            //             $('#tema-dropdown').removeAttr('disabled');
            //         }
            //         my_lst.anno = anni[index];
            //         create_green_select2('#year-dropdown', anni, anni[index].toString());
            //         index++;
            //         return index;
            //     }

            //     $("#play").html("<i class='fa fa-space-shuttle faa-passing animated'></i>").attr('disabled', 'disabled');
            //     $('#random').attr('disabled', 'disabled');
            //     $('#year-dropdown').attr('disabled', 'disabled');
            //     $('#metric-dropdown').attr('disabled', 'disabled');
            //     $('#tema-dropdown').attr('disabled', 'disabled');
            //     var anni = params.anni;
            //     var index = 0;
            //     showDataOverYear(index, anni);
            //     var playInterval = setInterval(function() {
            //         index = showDataOverYear(index, anni);
            //     }, 2000);
            // })


            $('#indicatore').text(params.tema);

            function apply_dropown(data, params){
                var data_subset = get_data_subset(data, params);
                var data_charts = get_data_for_chart(data_subset, map_data, params);
                var my_lst = add_filter_event_listner(Charts, data_subset, map_data, params);
                update_charts(data_charts, Charts.Italy, Charts.RegionChart, Charts.YearChart);
                updateInfo(data_charts.region);
            }

            function randomize_all(data){
                var params = getRandomParams(data);
                create_green_select2('#tema-dropdown', params.temi, params.tema, search=true, myclass='metric');
                delete_green_select2('#metric-dropdown');
                create_green_select2('#metric-dropdown', params.indicatori, params.indicatore, search=true, myclass='metric');
                delete_green_select2('#year-dropdown');
                create_green_select2('#year-dropdown', params.anni, params.anno);
                apply_dropown(data, params);
                return params
            }

            create_green_select2('#tema-dropdown', params.temi, params.tema, search=true, myclass='metric');
            create_green_select2('#metric-dropdown', params.indicatori, params.indicatore, search=true, myclass='metric');
            create_green_select2('#year-dropdown', params.anni, params.anno, search=false, myclass='year');

            $("#tema-dropdown").on("select2:select", function (e) {
                var tema = e.params.data.text;
                params = getRandomParams(data, tema=tema, indicatore=null, regione=params.regione);
                delete_green_select2('#metric-dropdown');
                create_green_select2('#metric-dropdown', params.indicatori, params.indicatore, search=true, myclass='metric');
                delete_green_select2('#year-dropdown');
                create_green_select2('#year-dropdown', params.anni, params.anno);
                apply_dropown(data, params);
            });

            $("#metric-dropdown").on("select2:select", function (e) {

                var indicatore = e.params.data.text;
                params = getRandomParams(data, tema=params.tema, indicatore=indicatore, regione=params.regione);

                delete_green_select2('#year-dropdown');
                create_green_select2('#year-dropdown', params.anni, params.anno);

                apply_dropown(data, params);

            });

            $("#year-dropdown").on("select2:select", function (e) {
                var anno = e.params.data.text
                params = getRandomParams(data, tema=params.tema, indicatore=params.indicatore, regione=params.regione, anno=anno);
                apply_dropown(data, params);
            });



            $('#random').on('click', function(d) {
                params = randomize_all(data);
                var btn = $(this);
                btn.attr('disabled', 'disabled');
                $('#year-dropdown').attr('disabled', 'disabled');
                $('#metric-dropdown').attr('disabled', 'disabled');
                $('#tema-dropdown').attr('disabled', 'disabled');
                var disableClick = setTimeout(function(){
                    $('#year-dropdown').removeAttr('disabled');
                    $('#metric-dropdown').removeAttr('disabled');
                    $('#tema-dropdown').removeAttr('disabled');
                    $(btn).removeAttr('disabled');

                }, 1000);
            });

        });
    }
//})


