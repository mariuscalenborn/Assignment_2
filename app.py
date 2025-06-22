from dash import Dash, dcc, html, Input, Output
import pandas as pd
import plotly.express as px
import json
from neighborhoods import zip_to_neighborhood
import plotly.graph_objects as go
import os

# prepping data
df = pd.read_csv("tickets.csv")
with open("Zipcodes_Poly.geojson", "r") as f:
    geojson_data = json.load(f)

# Data cleaning and preprocessing
df = df[df['zip_code'].notna()]
df['zip_code'] = df['zip_code'].astype(float).astype(int).astype(str).str.zfill(5)
df['fine'] = pd.to_numeric(df['fine'], errors='coerce')
df['issue_datetime'] = pd.to_datetime(df['issue_datetime'], utc=True)
df['date'] = df['issue_datetime'].dt.date

#helper function to convert zip codes to neighborhood labels
def zip_to_label(z):
    return " / ".join(zip_to_neighborhood.get(z, [f"ZIP {z}"]))

# Count violations per zip code and create a DataFrame for the choropleth
violation_counts = df['zip_code'].value_counts().reset_index()
violation_counts.columns = ['zip', 'violation_count']
violation_counts['neighborhoods'] = violation_counts['zip'].apply(zip_to_label)

app = Dash(__name__)
#==== Layout of the app ====
app.layout = html.Div([
    #Header with title and dropdown for agency selection'
    html.Div([
    html.Div([
        html.Div([
            html.H1("Parking Violations of Philadelphia", style={
                "margin": 0,
                "fontSize": "36px",
                "lineHeight": "1.2"
            }),
            html.Div("of 2017", style={
                "color": "#6c757d",
                "fontSize": "20px"
            })
        ], style={"flex": "1"}),
        html.Div([
            dcc.Dropdown(
                id='agency-dropdown',
                options=[{'label': agency, 'value': agency} for agency in sorted(df['issuing_agency'].dropna().unique())],
                placeholder="Select Issuing Agency",
                style={"width": "300px", "marginRight": "20px"}
            ), 
            html.Div(id='active-filters', style={"fontWeight": "bold", "whiteSpace": "nowrap"})
        ], style={
            "display": "flex",
            "alignItems": "center",
            "gap": "10px"
        })
    ], style={
        "display": "flex",
        "justifyContent": "space-between",
        "alignItems": "center",
        "marginBottom": "10px",
        "flexWrap": "wrap"
    })
], style={"margin": "20px"})
, 


    dcc.Store(id='filter-store', data={
        'zip': None,
        'time_range': None,
        'violations': [],
        'agency': None,
        'weekdays': []
    }),
    #map and plot layout
    html.Div([
        html.Div([
            dcc.Graph(id="map", style={
                'flex': '1',
                'width': '100%', 
                'borderRadius': '10px', 
                'boxShadow': '0 2px 6px rgba(0,0,0,0.1)', 
                'padding': '5px', 
                'backgroundColor': 'white'
                })
        ], style={
            'flex': '1',
            'minWidth': '300px', 
            'display': 'flex', 
            'flexDirection': 'column'
            }),

        html.Div([
            html.Div(dcc.Graph(id="avg_tickets_per_day", style={'height': '300px', 'width': '100%'}), style={'backgroundColor': 'white', 'borderRadius': '10px', 'padding': '10px', 'marginBottom': '10px'}),
            html.Div(dcc.Graph(id="revenue_plot", style={'height': '300px', 'width': '100%'}), style={'backgroundColor': 'white', 'borderRadius': '10px', 'padding': '10px', 'marginBottom': '10px'}),
            html.Div(dcc.Graph(id="time_series_plot", style={'height': '300px', 'width': '100%'}), style={'backgroundColor': 'white', 'borderRadius': '10px', 'padding': '10px', 'marginBottom': '10px'}),
            html.Div([
    html.Div(dcc.Graph(id="total_revenue", style={'height': '200px', 'width': '100%'}), style={
        'backgroundColor': 'white',
        'borderRadius': '10px',
        'padding': '10px',
        'flex': '1',
        'minWidth': '200px'
    }),
    html.Div(dcc.Graph(id="total_count", style={'height': '200px', 'width': '100%'}), style={
        'backgroundColor': 'white',
        'borderRadius': '10px',
        'padding': '10px',
        'flex': '1',
        'minWidth': '200px'
    })
], style={'display': 'flex', 'gap': '10px'})
], style={'flex': '1', 'minWidth': '300px'})
    ], style={'display': 'flex', 'flexWrap': 'wrap', 'margin': '20px', 'gap': '20px'})
], style={'backgroundColor': '#e5e8ec', 'minHeight': '100vh', 'paddingBottom': '0px', 'paddingTop' : '5px'})

#==== Callbacks ====
#first initial plotting and update logik for new inputs by the user
@app.callback(
    Output("map", "figure"),
    Output("revenue_plot", "figure"),
    Output("time_series_plot", "figure"),
    Output("total_revenue", "figure"),
    Output("avg_tickets_per_day", "figure"),
    Output("total_count", "figure"),          
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

# Filter the DataFrame based on user inputs

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
    

    # Choropleth
    fig_map = px.choropleth_mapbox(
        violation_counts,
        geojson=geojson_data,
        locations='zip',
        color='violation_count',
        featureidkey='properties.CODE',
        custom_data=['neighborhoods', 'violation_count'],
        mapbox_style='carto-positron',
        zoom=10.5,
        center={"lat": 40.0, "lon": -75.129508},
        opacity=0.5,


    )
    fig_map.update_traces(hovertemplate="<b>%{customdata[0]}</b><br>Anzahl Verstöße: %{customdata[1]}<extra></extra>",
                          marker_line_color='black',
                          marker_line_width=1)

    fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0},
                           showlegend=False,
                           paper_bgcolor='rgba(0,0,0,0)',
                            plot_bgcolor='rgba(0,0,0,0)',
                            autosize=True,
                            height=None
                           )
    fig_map.update_coloraxes(showscale=False)


    #highlight selected zip code
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
            lambda desc: 'red' if desc in selected_violations else '#636EFA'
        )
        fig_rev = px.bar(
            top_violations,
            x='violation_desc', y='fine',
            color='color',
            color_discrete_map="identity",
            title='Top 5 Violations by Revenue',
            category_orders={'violation_desc': top_violations['violation_desc'].tolist()}
        )
        fig_rev.update_layout(
    margin={"t": 40}, 
    xaxis_title=None, 
    yaxis_title=None, 
    showlegend=False,
    clickmode='event+select',
    xaxis_tickangle=-30,
    plot_bgcolor='white',
    paper_bgcolor='white',

    xaxis=dict(
        showline=True,
        ticks='outside',
        linecolor='LightGray',
        linewidth=1,
        showgrid=False,
        zeroline=False,
        showticklabels=True
    ),
    yaxis=dict(
        showgrid=True,
        gridcolor='LightGray',
        gridwidth=1,
        zeroline=False,
        griddash='dash',
        showticklabels=True
    )
)
        fig_rev.update_traces(
            hovertemplate="<b>%{x}</b><br>Revenue: $%{y:,.0f}<extra></extra>"
        )

        
        fig_rev.update_traces(marker_line_width=0, 
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
        title='Tickets over Time'
    )
    fig_time.update_layout(margin={"t": 40}, xaxis_title=None, yaxis_title=None,plot_bgcolor='white',
                              paper_bgcolor='white',
                              xaxis=dict(
        showline=True,
        ticks='outside',
        linecolor='LightGray',
        linewidth=1,
        showgrid=False,
        zeroline=False,
        showticklabels=True
    ),
    yaxis=dict(
        showgrid=True,
        gridcolor='LightGray',
        gridwidth=1,
        zeroline=False,
        griddash='dash',
        showticklabels=True
    )
                              )
    fig_time.update_traces(
        hovertemplate="<b>%{x}</b><br>Anzahl Tickets: %{y}<extra></extra>")

    # Total revenue
    total_sum = filtered_df['fine'].sum()
    fig_total = go.Figure(go.Indicator(
    mode="number",
    value=total_sum,
    number={
        "prefix": "$",
        "valueformat": ",.0f",
        "font": {"size": 40}
    },
    title={"text": "Total Revenue", "font": {"size": 18}}
))
    fig_total.update_layout(
    margin={"t": 30, "b": 0, "l": 0, "r": 0},
    paper_bgcolor="white",
    height=200
)

    # Total ticket count
    total_count = len(filtered_df)
    fig_count = go.Figure(go.Indicator(
    mode="number",
    value=total_count,
    number={
        
        "valueformat": ",.0f",
        "font": {"size": 40}
    },
    title={"text": "Total Ticket Count", "font": {"size": 18}}
))
    fig_count.update_layout(
    margin={"t": 30, "b": 0, "l": 0, "r": 0},
    paper_bgcolor="white",
    height=200
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
        lambda day: 'red' if day in selected_weekdays else '#636EFA'
    )

    fig_avg = px.bar(
        weekday_avg, x='weekday', y='avg_tickets',
        color='color',
        color_discrete_map="identity",
        title='Average Tickets per Day of the Week',
        category_orders={'weekday': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']}
    )

    fig_avg.update_layout(
        margin={"t": 40}, 
        xaxis_title=None, 
        yaxis_title=None,
        showlegend=False,
        clickmode='event+select',plot_bgcolor='white',
                              paper_bgcolor='white',

    xaxis=dict(
        showline=True,
        ticks='outside',
        linecolor='LightGray',
        linewidth=1,
        showgrid=False,
        zeroline=False,
        showticklabels=True
    ),
    yaxis=dict(
        showgrid=True,
        gridcolor='LightGray',
        gridwidth=1,
        zeroline=False,
        griddash='dash',
        showticklabels=True
    )
    )
    
    fig_avg.update_traces(
    hovertemplate="<b>%{x}</b><br>Durchschnittliche Tickets: %{y}<extra></extra>",
    marker_line_width=0,
    
    selector=dict(type='bar')
    )

    # text for current neighborhood
    desc = []
    if selected_zip:
        neighborhoods = zip_to_neighborhood.get(selected_zip, [f"ZIP {selected_zip}"])
        filter_text = " | ".join(neighborhoods)
    else:
        filter_text = "All Neighborhoods"


    return (
        fig_map,
        fig_rev,
        fig_time,
        fig_total,
        fig_avg,
        fig_count,                      
        f"Neighborhood: {filter_text}"
    )

# === Interactivity for the map and plots ===
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
    # filter store to hold the current state of the filters
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
    port = int(os.environ.get("PORT", 8050))  # Fallback für lokal
    app.run(host="0.0.0.0", port=port, debug=False)

