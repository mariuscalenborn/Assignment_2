from dash import Dash, dcc, html, Input, Output, State
import pandas as pd
import plotly.express as px
import json

# 📁 Daten vorbereiten
df = pd.read_csv("tickets.csv")
with open("Zipcodes_Poly.geojson", "r") as f:
    geojson_data = json.load(f)

df = df[df['zip_code'].notna()]
df['zip_code'] = df['zip_code'].astype(float).astype(int).astype(str).str.zfill(5)
df['fine'] = pd.to_numeric(df['fine'], errors='coerce')
df['issue_datetime'] = pd.to_datetime(df['issue_datetime'], utc=True)
df['date'] = df['issue_datetime'].dt.date

zip_to_neighborhood = {
    "19102": ["Center City", "Rittenhouse", "Logan Square", "Penn Center", "Avenue of the Arts"],
    "19103": ["Center City", "Avenue of the Arts", "Logan Circle", "Rittenhouse"],
    "19104": ["University City", "West Philadelphia", "Belmont"],
    "19106": ["Old City", "Society Hill", "Penn’s Landing"],
    "19107": ["Center City North", "Chinatown"],
    "19108": ["Fairmount", "Poplar"],
    "19109": ["Center City", "Washington Square West"],
    "19110": ["Northern Liberties", "Olde Kensington"],
    "19111": ["Frankford", "Wissinoming"],
    "19112": ["Mayfair"],
    "19114": ["West Oak Lane", "Academy Gardens"],
    "19115": ["Fox Chase", "Holmesburg"],
    "19116": ["Holmesburg"],
    "19118": ["Somerton", "Bustleton"],
    "19119": ["Mount Airy"],
    "19120": ["Germantown"],
    "19121": ["Brewerytown", "Francisville"],
    "19122": ["Kensington", "Fishtown"],
    "19123": ["Spring Garden", "Old City West"],
    "19124": ["Frankford"],
    "19125": ["Northern Liberties", "Fishtown"],
    "19126": ["East Falls"],
    "19127": ["Manayunk", "Roxborough"],
    "19128": ["Angora", "Overbrook"],
    "19129": ["Powelton Village", "West Powelton"],
    "19130": ["Fairmount", "Spring Garden", "Art Museum area"],
    "19131": ["Overbrook", "Wynnefield", "Belmont"],
    "19132": ["Tioga", "Nicetown", "Germantown"],
    "19133": ["North Philadelphia East", "Strawberry Mansion"],
    "19134": ["Port Richmond"],
    "19135": ["Tacony"],
    "19136": ["Holmesburg", "Torresdale"],
    "19137": ["Bridesburg", "Port Richmond"],
    "19138": ["Cedarbrook"],
    "19139": ["Manayunk", "East Falls"],
    "19140": ["Frankford"],
    "19141": ["Mayfair"],
    "19142": ["Pennypack", "Holmesburg"],
    "19143": ["Pennsport", "South Philadelphia"],
    "19144": ["Olney"],
    "19145": ["Graduate Hospital", "Southwest Center City"],
    "19146": ["West Philadelphia", "Graduate Hospital"],
    "19147": ["Bella Vista", "Italian Market"],
    "19148": ["Navy Yard", "South Philadelphia"],
    "19149": ["East Germantown"],
    "19150": ["Eastwick"],
    "19151": ["Kingsessing"],
    "19152": ["Airport area"],
    "19153": ["Clearview"],
    "19154": ["Bartram Village"]
}

def zip_to_label(z):
    return " / ".join(zip_to_neighborhood.get(z, [f"ZIP {z}"]))

violation_counts = df['zip_code'].value_counts().reset_index()
violation_counts.columns = ['zip', 'violation_count']
violation_counts['neighborhoods'] = violation_counts['zip'].apply(zip_to_label)

app = Dash(__name__)

app.layout = html.Div([
    html.Div(id='active-filters', style={'margin': '10px', 'fontWeight': 'bold'}),
    dcc.Dropdown(
    id='agency-dropdown',
    options=[
        {'label': agency, 'value': agency} 
        for agency in sorted(df['issuing_agency'].dropna().unique())
    ],
    placeholder="Select Issuing Agency",
    style={'width': '300px', 'marginBottom': '10px'}
),

    dcc.Store(id='filter-store', data={
        'zip': None,
        'time_range': None,
        'violations': [],
        'agency': None, 
        'weekdays': []
    }),
    html.H4('Anzahl Parkverstöße pro Stadtteil in Philadelphia'),

html.Div([
    
    html.Div([
        dcc.Graph(id="map", style={'height': '100%', 'width': '100%'})
    ], style={'flex': '1', 'paddingRight': '15px'}),

    
    html.Div([
        dcc.Graph(id="revenue_plot", style={'height': '300px'}),
        dcc.Graph(id="time_series_plot", style={'height': '300px'}),
        dcc.Graph(id="total_revenue", style={'height': '250px'}),
        dcc.Graph(id="avg_tickets_per_day", style={'height': '250px'}),
    ], style={'flex': '1'})
], style={'display': 'flex', 'height': '100%', 'gap': '10px'})
])

#first initial plotting and update logik for new inputs by the user
@app.callback(
    Output("map", "figure"),
    Output("revenue_plot", "figure"),
    Output("time_series_plot", "figure"),
    Output("total_revenue", "figure"),
    Output("avg_tickets_per_day", "figure"),
    Output("active-filters", "children"),
    Input("filter-store", "data")
)
def update_all(filter_data):
    selected_zip = filter_data.get('zip')
    time_range = filter_data.get('time_range')
    selected_violations = filter_data.get('violations', [])
    selected_agency = filter_data.get('agency')
    selected_weekdays = filter_data.get('weekdays', [])

    filtered_df = df.copy()
    title_suffix = ""

    if selected_zip:
        filtered_df = filtered_df[filtered_df['zip_code'] == selected_zip]
        neighborhoods = zip_to_neighborhood.get(selected_zip, [f"ZIP {selected_zip}"])
        title_suffix += " – " + ", ".join(neighborhoods)

    if time_range:
        start, end = pd.to_datetime(time_range[0]), pd.to_datetime(time_range[1])
        if start.tzinfo is None:
            start = start.tz_localize("UTC")
        if end.tzinfo is None:
            end = end.tz_localize("UTC")
        filtered_df = filtered_df[(filtered_df['issue_datetime'] >= start) & (filtered_df['issue_datetime'] <= end)]
        title_suffix += f" – Zeitraum {start.date()} bis {end.date()}"

    if selected_agency:
        filtered_df = filtered_df[filtered_df['issuing_agency'] == selected_agency]
        title_suffix += f" – Agentur: {selected_agency}"

    filtered_for_avg = filtered_df.copy()

    if selected_weekdays:
        filtered_df = filtered_df[filtered_df['issue_datetime'].dt.day_name().isin(selected_weekdays)]
        title_suffix += f" – Wochentage: {', '.join(selected_weekdays)}"

    filtered_for_rev = filtered_df.copy()

    if selected_violations:
        filtered_df = filtered_df[filtered_df['violation_desc'].isin(selected_violations)]
        title_suffix  += " – Gefilterte Verstöße"
        filtered_for_avg = filtered_for_avg[filtered_for_avg['violation_desc'].isin(selected_violations)]
    
    
    if selected_zip:
        filtered_for_avg = filtered_for_avg[filtered_for_avg['zip_code'] == selected_zip]
    if time_range:
        filtered_for_avg = filtered_for_avg[(filtered_for_avg['issue_datetime'] >= start) & (filtered_for_avg['issue_datetime'] <= end)]
    if selected_agency:
        filtered_for_avg = filtered_for_avg[filtered_for_avg['issuing_agency'] == selected_agency]
    if selected_violations:
        filtered_for_avg = filtered_for_avg[filtered_for_avg['violation_desc'].isin(selected_violations)]
    

    # 🗺️ Choroplethenkarte bleibt unverändert
    fig_map = px.choropleth_mapbox(
        violation_counts,
        geojson=geojson_data,
        locations='zip',
        color='violation_count',
        featureidkey='properties.CODE',
        custom_data=['neighborhoods', 'violation_count'],
        mapbox_style='open-street-map',
        zoom=10.5,
        center={"lat": 40.0, "lon": -75.129508},
        opacity=0.3,
        title='Anzahl Parkverstöße pro Stadtteil'
    )
    fig_map.update_traces(hovertemplate="<b>%{customdata[0]}</b><br>Anzahl Verstöße: %{customdata[1]}<extra></extra>",
                          marker_line_color='black',
                          marker_line_width=1.5)

    fig_map.update_layout(margin={"r":0,"t":40,"l":0,"b":0}, showlegend=False)
    fig_map.update_coloraxes(showscale=False)

    if selected_zip:
        zip_row = violation_counts[violation_counts['zip'] == selected_zip]
        if not zip_row.empty:
            highlight_df = pd.DataFrame({
                'zip': zip_row['zip'].values,
                'highlight': [1],
                'neighborhoods': zip_row['neighborhoods'].values,
                'violation_count': zip_row['violation_count'].values
        })

            highlight_layer = px.choropleth_mapbox(
                highlight_df,
                geojson=geojson_data,
                locations='zip',
                color='highlight',
                featureidkey='properties.CODE',
                color_continuous_scale=['red', 'red'],
                custom_data=['neighborhoods', 'violation_count'],
                opacity=0.8
        )

            highlight_layer.update_traces(
                hovertemplate="<b>%{customdata[0]}</b><br>Anzahl Verstöße: %{customdata[1]}<extra></extra>"
        )

            fig_map.add_trace(highlight_layer.data[0])


    # Revenue Bar Chart per violation
    valid_violations = filtered_for_rev[['violation_desc', 'fine']].dropna()
    if not valid_violations.empty:
        top_violations = (
            valid_violations.groupby('violation_desc')['fine']
            .sum().reset_index()
            .sort_values(by='fine', ascending=False)
            .head(5)
        )
        top_violations['color'] = top_violations['violation_desc'].apply(
            lambda desc: 'red' if desc in selected_violations else 'lightgray'
        )
        fig_rev = px.bar(
            top_violations,
            x='violation_desc', y='fine',
            color='color',
            color_discrete_map="identity",
            title='Top 5 Verstöße nach Revenue' + title_suffix,
            category_orders={'violation_desc': top_violations['violation_desc'].tolist()}
        )
        fig_rev.update_layout(margin={"t": 40}, 
                              xaxis_title=None, 
                              yaxis_title=None, 
                              showlegend=False,
                              clickmode='event+select',
                              xaxis_tickangle=-45)
        
        fig_rev.update_traces(marker_line_width=2, 
                              marker_line_color='black',
                              selector=dict(type='bar')
        )
    else:
        fig_rev = px.bar(title='Keine gültigen Verstöße gefunden' + title_suffix)

    # timeseries line chart 
    time_series = (
        filtered_df.groupby(filtered_df['issue_datetime'].dt.date)
        .size().reset_index(name='ticket_count')
    )
    fig_time = px.line(
        time_series, x='issue_datetime', y='ticket_count',
        title='Tickets über Zeit' + title_suffix
    )
    fig_time.update_layout(margin={"t": 40}, xaxis_title=None, yaxis_title=None)

    # Total revenue
    total_sum = filtered_df['fine'].sum()
    fig_total = px.scatter(
        x=[0], y=[0],
        text=[f"${total_sum:,.0f}"],
        title="Gesamte Strafsumme" + title_suffix
    )
    fig_total.update_traces(textfont_size=48, mode="text")
    fig_total.update_layout(
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        showlegend=False, margin={"t": 40}
    )

    # Weekday Avg
    filtered_for_avg['weekday'] = filtered_for_avg['issue_datetime'].dt.day_name()
    filtered_for_avg['date'] = filtered_for_avg['issue_datetime'].dt.date
    weekday_counts = filtered_for_avg.groupby(['date', 'weekday']).size().reset_index(name='daily_count')
    weekday_avg = (
        weekday_counts.groupby('weekday')['daily_count']
        .mean().round().astype(int)
        .reindex(['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'])
        .reset_index(name='avg_tickets')
    )
    weekday_avg['color'] = weekday_avg['weekday'].apply(
        lambda day: 'red' if day in selected_weekdays else 'lightgray'
    )

    fig_avg = px.bar(
        weekday_avg, x='weekday', y='avg_tickets',
        color='color',
        color_discrete_map="identity",
        title='Ø Tickets pro Wochentag' + title_suffix,
        category_orders={'weekday': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']}
    )

    fig_avg.update_layout(
        margin={"t": 40}, 
        xaxis_title=None, 
        yaxis_title=None,
        showlegend=False,
        clickmode='event+select'
    )
    
    fig_avg.update_traces(
    marker_line_width=2,
    marker_line_color='black',
    selector=dict(type='bar')
    )

    # 🧾 Aktive Filteranzeige
    desc = []
    if selected_zip:
        desc.append(f"ZIP: {selected_zip}")
    if time_range:
        desc.append(f"Zeitraum: {start.date()} bis {end.date()}")
    if selected_violations:
        desc.append(f"Verstöße: {', '.join(selected_violations)}")
    if selected_agency:
        desc.append(f"Agentur: {selected_agency}")
    filter_text = " | ".join(desc) if desc else "Keine Filter aktiv"

    return fig_map, fig_rev, fig_time, fig_total, fig_avg, f"Aktive Filter: {filter_text}"

@app.callback(
    Output("filter-store", "data"),
    Input("map", "clickData"),
    Input("time_series_plot", "relayoutData"),
    Input("revenue_plot", "selectedData"),
    Input("agency-dropdown", "value"),
    Input("avg_tickets_per_day", "selectedData"),
    prevent_initial_call=True
)
def update_filter_store(clickData, relayoutData, selectedData, agency, selectedWeekdays):
    store = {'zip': None, 
             'time_range': None, 
             'violations': [],
             'agency': None,
             'weekdays': []
}
             
    if clickData and "points" in clickData:
        clicked_zip = clickData["points"][0]["location"]
        current_zip = store.get('zip')
        if current_zip == clicked_zip:
            store['zip'] = None
        else:
            store['zip'] = clicked_zip
            
    if relayoutData and "xaxis.range[0]" in relayoutData:
        store['time_range'] = [
            relayoutData["xaxis.range[0]"],
            relayoutData["xaxis.range[1]"]
        ]

    if selectedWeekdays and "points" in selectedWeekdays:
        store['weekdays'] = [pt["x"] for pt in selectedWeekdays["points"]]

    if selectedData and "points" in selectedData:
        store['violations'] = [pt["x"] for pt in selectedData["points"]]

    store['agency'] = agency

    return store

if __name__ == '__main__':
    app.run(debug=True)
