function format_geo_data(map_data){
    map_data.features.forEach(function(d) {
        d.properties.name = d.properties.name.replace(/ /g, '-');
    })
    return map_data.features;
}

function format_data(data){

    data.forEach(function(d) {
        d['Dato'] = +d['Dato'].replace(',', '.');
        d['Regione'] = d['Territorio'].replace(/'/g, ' ').replace(/ /g, '-').toLowerCase();
        d['Anno'] = +d['Anno'];
        d['Indicatore'] = d['Indicatore'].replace(/"/g,  "'");
    })

    return data;
}

function get_values_for_theme(data, tema){
    return data.filter(function(d){ return d.Tema == tema });
}

function get_values_for_indicator(data, indicatore){
    return data.filter(function(d){ return d.Indicatore == indicatore });
}

function get_values_for_year(data, anno){
    return data.filter(function(d){ return d.Anno == anno });
}

function get_values_for_region(data, regione){
    return data.filter(function(d){ return d.Regione == regione });
}

function get_values_for_map(data, geo_data, params){
    data = data.filter(function(d){return (d.Indicatore == params.indicatore && d.Anno == params.anno)});
    geo_data.forEach(function(d) { data = replace_missing_value(data, d.properties.name );
        v = data.filter(function(f) { return d.properties.name == f.Regione });
        d = Object.assign(d, v[0]);
    });
    return geo_data;
}

function get_data_subset(data, params){
    return data.filter(function(d){return d.Indicatore == params.indicatore && d.Tema == params.tema });
}

function get_data_for_chart(data, geo_data, params){
    return {'year': get_values_for_region(data, params.regione),
            'region': get_values_for_year(data, params.anno),
            'map': get_values_for_map(data, geo_data, params)};
}

function update_charts(c_data, c_map=false, c_region=false, c_year=false){
    (c_map) ? c_map.data(c_data.map).update() : null;
    (c_region) ? c_region.data(c_data.region).update() : null;
    (c_year) ? c_year.data(c_data.year).update() : null;
}


function init_chart(y_data, r_data, m_data, params){

    YearChart = new TimeBarChart('#timechart').data(y_data).height(200).interpolate(true);
    RegionChart = new BarChart('#barchart').data(r_data).height(400);
    Italy = new ItalyMap('#map').data(m_data).indicatore(params.indicatore);

    YearChart().update(); RegionChart().update(); Italy();

    return {YearChart: YearChart, RegionChart: RegionChart, Italy: Italy};
}

function selectCharts(params){
    var bars = d3.selectAll('#timechart rect')
    bars.style('fill', 'url(#svgGradient2)').classed("selected", false);
    d3.select('#timechart rect#y'+params.anno).style('fill', '#464647').classed("selected", true)

    var bars = d3.selectAll('#barchart rect');
    bars.style('fill', 'url(#svgGradient)').classed("selected", false);
    d3.select('#barchart rect#'+params.regione).style('fill', '#464647').classed("selected", true);

}


function add_filter_event_listner(Charts, data, geo_data, params){

    var listner = {
        _anno: params.anno,
        get anno() { return this._anno; },
        set anno(value) {
            this._anno = value;
            params.anno = value;
            console.log(params)
            var charts_dataset = get_data_for_chart(data, geo_data, params);
            update_charts(charts_dataset, Charts.Italy, Charts.RegionChart, Charts.YearChart);
            //selectCharts(params);

        },
        _regione: params.regione,
        get regione() { return this._regione; },
        set regione(value) {
            this._regione = value;
            params.regione = value;
            console.log(params)
            var charts_dataset = get_data_for_chart(data, geo_data, params);
            update_charts(charts_dataset, Charts.Italy, Charts.RegionChart, Charts.YearChart);
            //selectCharts(params);
        },

    };
    for (chart in Charts){
        Charts[chart].event_listner(listner);
    }
    return listner
}

