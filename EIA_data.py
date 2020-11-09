# Gets EIA data for hourly demand for Texas and ERCOT South Central
# creates a notional 2018 year for hourly electrical demand in ERCOT SCEN
import sys, os
print(sys.version, '\n')
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.cbook as cbook
import json
from urllib.error import URLError, HTTPError
from urllib.request import urlopen
from datetime import datetime
from pandas.plotting import register_matplotlib_converters
register_matplotlib_converters()

os.environ["EIA_KEY"]="ba1be1ff6d258c3b793079d6fbc47131"

years = mdates.YearLocator()
months = mdates.MonthLocator()
years_fmt = mdates.DateFormatter('%Y')

from eiapy import Series
tx = Series('EBA.TEX-ALL.D.H')
tx_south = Series('EBA.ERCO-SCEN.D.H')

print(type(tx_south))

class EIAgov(object):
    def __init__(self, token, series):
        '''
        Purpose:
        Initialise the EIAgov class by requesting:
        - EIA token
        - id code(s) of the series to be downloaded

        Parameters:
        - token: string
        - series: string or list of strings
        '''
        self.token = token
        self.series = series

    '''
    def __repr__(self):
        return str(self.series)
    '''

    def Raw(self, ser):
        # Construct url
        url = 'http://api.eia.gov/series/?api_key=' + self.token + '&series_id=' + ser.upper()

        try:
            # URL request, URL opener, read content
            response = urlopen(url);
            raw_byte = response.read()
            raw_string = str(raw_byte, 'utf-8-sig')
            jso = json.loads(raw_string)
            return jso

        except HTTPError as e:
            print('HTTP error type.')
            print('Error code: ', e.code)

        except URLError as e:
            print('URL type error.')
            print('Reason: ', e.reason)

    def GetData(self):
        # Deal with the date series
        date_ = self.Raw(self.series[0])
        date_series = date_['series'][0]['data']
        endi = len(date_series) # or len(date_['series'][0]['data'])
        date = []
        for i in range (endi):
            date.append(date_series[i][0])

        # Create dataframe
        df = pd.DataFrame(data=date)
        df.columns = ['Date']

        # Deal with data
        lenj = len(self.series)
        for j in range (lenj):
            data_ = self.Raw(self.series[j])
            data_series = data_['series'][0]['data']
            data = []
            endk = len(date_series)
            for k in range (endk):
                data.append(data_series[k][1])
            df[self.series[j]] = data

        return df

if __name__ == '__main__':
    tok = 'ba1be1ff6d258c3b793079d6fbc47131'

  	# Texas hourly electricity demand
    tx = ['EBA.TEX-ALL.D.H']
    data = EIAgov(tok, tx)
    tx = data.GetData()
    tx = tx.rename(columns = {'EBA.TEX-ALL.D.H':'demand'})

    # Texas hourly electricity demand
    tx_south = ['EBA.ERCO-SCEN.D.H']
    dataTxS = EIAgov(tok, tx_south)
    tx_s = dataTxS.GetData()
    tx_s = tx_s.rename(columns = {'EBA.ERCO-SCEN.D.H':'demand'})

# convert date and time info to datetime object
def cleanUpDateTime(df):
    # creates a function to convert from string to datetime info
    # still need to add info to keep time zone info
    df['DateTime'] = ""
    for n in range(df.shape[0]):
        y = df.Date[n].replace("T", "")
        z = y.replace("Z", "")
        df['DateTime'][n] = datetime.strptime(z, '%Y%m%d%H')
    return(df)

tx = cleanUpDateTime(tx)
tx_s = cleanUpDateTime(tx_s)

# make a figure
def plotTXandTXSouth(demandData, figName):

    plt.figure(figsize=(5,3))

    fig, ax = plt.subplots()

    # rotate and align the tick labels so they look better
    fig.autofmt_xdate()

    plt.plot(demandData.DateTime, demandData.demand)

    ax.set_title('Power Demand')
    plt.ylim(0)
    ax.set_xlabel('Date')
    ax.set_ylabel('Demand (in MW-hrs')

    plt.savefig(figName, dpi=300)

plotTXandTXSouth(tx, 'HourlyTexasElecDemand.png')
plotTXandTXSouth(tx_s, 'HourlyTexasSouthElecDemand.png')
