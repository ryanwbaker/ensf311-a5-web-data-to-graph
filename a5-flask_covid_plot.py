# Author: Ryan Baker
import sqlite3
from flask import Flask, render_template
from flask import g # Keeping state: contains database connection
import pandas as pd
from datetime import datetime

# Used for plotting to memory and converting to ascii stream
import base64
from io import BytesIO

from matplotlib.figure import Figure
from matplotlib.ticker import FormatStrFormatter
import seaborn as sns

app = Flask(__name__)


DATABASE='data/measurements.db'

# From: https://flask.palletsprojects.com/en/1.1.x/patterns/sqlite3/
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db
    
def get_df_from_db(start_date=None, end_date=None):
    # without a date range, we select all data
    if start_date is None and end_date is None:
        query = "select * from alberta"
    else: # checking if date range is valid, construct sql query with between
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d' )
        except:
            # default start date is prior to pandemic
            start_date = '2020-01-01'
        try:
            end_date = datetime.strptime(end_date, '%Y-%m-%d' )
        except:
            # default end date is today
            end_date = datetime.today().strftime('%Y-%m-%d' )
        query = f"select * from alberta where date between '{start_date}' and '{end_date}'"
        
    df = pd.read_sql_query(query, con=get_db(), parse_dates=['date'])
    df['total_cases'] = df['daily_cases'].cumsum()
    # min_periods=1 avoids NaN at the start
    df['smooth_daily_cases'] = df['daily_cases'].rolling(7, min_periods=1).mean()

    return df

#From: https://matplotlib.org/devdocs/gallery/user_interfaces/web_application_server_sgskip.html
def get_image_from_fig(fig):
    # Save it to a temporary buffer.
    buf = BytesIO()
    fig.savefig(buf, format="png")
    # Embed the result in the html output.
    data = base64.b64encode(buf.getbuffer()).decode("ascii")
    return f"<img src='data:image/png;base64,{data}'/>"

# From: https://flask.palletsprojects.com/en/1.1.x/patterns/sqlite3/
@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# TODO: add '/' route and view function to render index.html
@app.route('/')
def index():
    return render_template('index.html',
                            title="Home")
@app.route('/daily')
def daily():
    df = get_df_from_db()

    fig = Figure()
    ax = fig.subplots()

    sns.lineplot(x='date', y='smooth_daily_cases', data=df, ax=ax)
    ax.tick_params(axis="x", which="both", rotation=45)
    ax.grid(b=True)

    fig.tight_layout()

    return render_template('plot.html', 
                            title="Daily Case Count", 
                            image_tag=get_image_from_fig(fig),
                            menu_items=[{'route':'/', 'desc':'Home'},{'route':'/total', 'desc':'Total Cases'},{'route':'/loglog', 'desc':'Log-Log Graph'}])
    

# TODO: add '/total' route and view function to render plot.html with total infections plot
@app.route('/total')
def total():
    df = get_df_from_db()

    fig = Figure()
    ax = fig.subplots()

    sns.lineplot(x='date', y='total_cases', data=df, ax=ax)
    ax.tick_params(axis="x", which="both", rotation=45)
    ax.grid(b=True)

    fig.tight_layout()

    return render_template('plot.html', 
                            title="Total Cases", 
                            image_tag=get_image_from_fig(fig),
                            menu_items=[{'route':'/', 'desc':'Home'},{'route':'/daily', 'desc':'Daily Case Count'},{'route':'/loglog', 'desc':'Log-Log Graph'}])

# TODO: add '/loglog' route and view function to render plot.html with Log-Log plot
@app.route('/loglog')
def loglog():
    df = get_df_from_db()

    fig = Figure()
    ax = fig.subplots()

    x_str='total_cases'
    y_str='smooth_daily_cases'
    # using log-log and two minor ticks per decade
    ax.loglog(df[x_str], df[y_str], subs=[2, 5])
    # Add a 'dot' to indicate last measurement
    ax.plot(df[x_str].iloc[-1], df[y_str].iloc[-1], 'ko')

    ax.set_xlabel(x_str)
    ax.set_ylabel(y_str)
    # grid on both major and minor ticks
    ax.grid(which='both')
    # major and minor tick labels as regular numbers
    ax.xaxis.set_major_formatter(FormatStrFormatter("%.0f"))
    ax.xaxis.set_minor_formatter(FormatStrFormatter("%.0f"))
    ax.yaxis.set_major_formatter(FormatStrFormatter("%.0f"))
    ax.yaxis.set_minor_formatter(FormatStrFormatter("%.0f"))

    # re-adjusting layout after rotating labels
    ax.tick_params(axis="x", which="both", rotation=45)
    fig.tight_layout()

    return render_template('plot.html', 
                            title="Log-Log Graph", 
                            image_tag=get_image_from_fig(fig),
                            menu_items=[{'route':'/', 'desc':'Home'},{'route':'/daily', 'desc':'Daily Case Count'},{'route':'/total', 'desc':'Total Cases'}])

if __name__ == '__main__':
    app.debug = True
    # use host='0.0.0.0' to access from other devices
    app.run(host='0.0.0.0')