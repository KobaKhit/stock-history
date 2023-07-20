import streamlit as st
import pandas as pd
# import plotly as pl
import altair as al
import yfinance as yf
from datetime import datetime

currentYear = datetime.now().year

st.set_page_config(layout="wide")

def local_css(file_name):
    '''
    Read in and apply user defined css.

    Args:
        file_name (str): path to the css file.

    Return:
        Nothing

    '''
    with open(file_name) as f:
        st.markdown('<style>{}</style>'.format(f.read()), unsafe_allow_html=True)

# local_css('dark.css')

@st.cache_data
def get_ticker_history(ticker, print_info = False):
    '''
    Retrieve Ticker history from yahoo finance.
    Argument ticker can be a list of tickers.
    '''

    if type(ticker)==list: # if list download data for every ticker.
        tickers = []
        for t in ticker:
            temp = get_ticker_history(t)
            temp = temp.reset_index()
            temp['ticker'] = t
            tickers.append(temp)
        return pd.concat(tickers, axis=0)

    ticke = yf.Ticker(ticker)
    # get stock info
    if print_info:
        print(ticke.info['shortName'])

    # get historical market data
    hist = ticke.history(period="max")

    return hist

st.title('🚀💸Stock History📉📈')

c1,c2 = st.columns([3,9])
with c1:
    ticker = st.text_input('Enter the Ticker', placeholder = 'SPY')
if ticker == '': ticker = 'SPY'

al.data_transformers.disable_max_rows() # remove 5k rows limit
al.themes.enable('dark') # set dark theme


df = get_ticker_history([ticker])
if df.empty: 
    st.error(f'Ticker \${ticker.upper()} is not available.')
    st.stop()

# df.to_csv('data.csv')
# df.head(2)

## Line Chart data
df['date'] = df.Date
df['month_day'] = [d.month*100 + d.day for d in df.date]
df['year'] = [str(d.year) for d in df.date]
df['year2'] = df.year

minYear = min(df.year)
minFilteredYear = max(int(minYear),int(currentYear)-25)

with c2:
    year_range = st.slider(
        "",
        value = (minFilteredYear,int(currentYear)),
        min_value = int(minYear),
        max_value = int(currentYear))

df = df[df.year.astype(int).between(*year_range)]
# calculate expanding pct change by year
df['ytd_pct_chng'] = df.groupby('year')['Close'].apply(lambda x: x.div(x.iloc[0]).subtract(1)).values
# print(f'Original df {df.shape}:\n',df.head(2),'\n')

## Correlation Chart data
corrMat = df.pivot(index=['month_day'], columns = ['year'])['Close'].corr().stack()
corrMat.index.names = ["year", "year2"]
corrMat = corrMat.reset_index().rename(columns={0:'corr'})
corrMat = corrMat[~corrMat[['year','year2']].apply(frozenset, axis=1).duplicated()] # remove duplicate pairs

correlated_years = corrMat[(corrMat.year2==str(currentYear)) & (corrMat.year!=str(currentYear))].sort_values(by='corr', key=abs, ascending = False)[['year','corr']].values[:2]

with st.expander('About'):
    st.markdown(f'''
    This dashboard shows percent change in \${ticker.upper()} price or any other Ticker available on `yfinance` which you can enter above.

    Using the correlation map below we can see that {currentYear} was most correlated to {correlated_years[0][0]} ({round(100*correlated_years[0][1])}%) and {correlated_years[1][0]} ({round(100*correlated_years[1][1])}%). If you hover over the correlation map, the corresponding year pairs will be highlighted in the line chart.

    I used yahoo finance to get the data and altair for plotting charts. Altair is a powerful declarative python plotting library based on vega. I like it for its crossfiltering feature where one can define interactions between charts. 
    
    ''')

    st.write("Check out the non streamlit version of this dash for only SPY on my [website](https://kobakhit.com/data-visuals/spy-history/spy-history.html).")

# corrMat
# print(f'Correlation df {corrMat.shape}:\n',corrMat.head(),'\n')

## Horizontal Bar data
# calculate percent change
annual = df.groupby('year')['Close'].apply(lambda x: pd.Series.pct_change(x).sum()).reset_index()
# print(f'Annual Change df {annual.shape}:\n',annual.head(3))

## Line Chart
# define base chart
base = al.Chart(df,title=f"Every Year of {ticker}, {year_range[0]} - {year_range[1]}").mark_line(interpolate='basis').encode(
    x=al.X('monthdate(date):O', title='',  axis=al.Axis(labelAngle=-45)),
    y=al.Y('ytd_pct_chng:Q', title='Percent Change YTD', axis=al.Axis(format='%')),
    detail='year',
    color = al.condition(f"datum.year == '{currentYear}'", al.value('red'), al.value('grey')),
    tooltip=['date',al.Tooltip('ytd_pct_chng', format=".0%")]
).properties(
    width=950,
    height=350
)

# add highlight on hover selector
highlight = al.selection(type='single', on='mouseover',
                          fields=['year'], nearest=True)

points = base.mark_circle().encode(
    opacity=al.value(0)
).add_selection(
    highlight
)

spy_line = (points)
# spy_line

## Correlation Map
# define base chart
corr = al.Chart(corrMat, title='Correlation by year').mark_rect().encode(
    x=al.X('year', title=None, sort='ascending', axis=al.Axis(orient="top",labelAngle=-45)),
    y=al.Y('year2', title=None, sort='descending'),
    color=al.Color('corr', legend=None),
    tooltip=['year','year2',al.Tooltip('corr', format=".0%")]
).properties(
    width=700,
    height=650
)
# add colored labels 
text = corr.mark_text(size=9).encode(
    al.Text('corr:Q', format=".0%"),
    color=al.condition(
        'datum.corr > 0',
        al.value('black'),
        al.value('white')
    )
)

# define year selector and add to correlation chart
year_selector = al.selection_single(fields=['year','year2'],on = 'mouseover',name='year_selector')
spy_corr = corr

if len(df.year.unique()) < 32:
    spy_corr = (spy_corr + text)

spy_corr = spy_corr.add_selection(
    year_selector
)
# spy_corr

## Horizonthal Bar Chart

# define base
bar = al.Chart(annual, title='Annual Percent Change').mark_bar().encode(
    x=al.X('Close:Q',title='', axis=al.Axis(format=".0%", orient="top")),
    y=al.Y("year:O",sort='descending'),
    tooltip=['year',al.Tooltip('Close', format=".0%")],
    color=al.condition(
        'datum.Close > 0',
        al.value('#4c78a8'),
        al.value('red')
    )
).properties(width=150,height=650)

# add labels
text = bar.mark_text(
    align='left',
).encode(
    text=al.Text('Close:Q',format='.0%'),
    color=al.value('white')
)
bar = (bar+text)
# bar

## Add crossfiltering

# vega expression for years selected in correlation map
year_selector_expr = '''
indexof(datum.year, year_selector.year) >= 0 || indexof(datum.year, year_selector.year2) >= 0
'''

# color conditions for line chart
color={
    'condition': [
        {"value":"white", "test": year_selector_expr},
        {"value":"red", "test": f"datum.year == {currentYear}"},
        {"value":"grey", "test": f"datum.year != {currentYear}"}
    ]
}

# add color interactions and custom legend to line chart
spy_line2 = (spy_line+base.mark_line().encode(
    color=al.Color('year',
                   scale=al.Scale(domain=[currentYear],range=['red']),
                   condition=color['condition'], 
                   legend=al.Legend(title='',orient='bottom-left',labelFontSize=18,symbolSize=400,symbolStrokeWidth=3,offset=40)),
    size=al.condition(year_selector_expr,al.value(2),al.value(1)),
).add_selection(year_selector))


view = (spy_line2 & (spy_corr | bar)) \
    .configure_title(fontSize=18) \
    .configure(background='rgb(14 17 23)') \
    .properties(center=True, autosize='fit')

_,c,_ = st.columns([1,8,4])
with c:
    st.altair_chart(view)