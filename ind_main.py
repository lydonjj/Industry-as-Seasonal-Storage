import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import ind_output as ind
from datetime import date
import matplotlib.ticker as ticker

def process(naics):
    #Gets data and organizes it. Takes average of capacity data and sum of emissions. Also gets all NAICS codes from FRED and EPA.
    cap = ind.Fred_data(naics)
    capacity, all_fred = cap.getData()
    capacity = capacity.mean(axis=0)

    emi = ind.EPA_data(naics)
    emissions, all_epa = emi.getData()
    emissions = emissions.sum(axis=0, numeric_only=True) / 1000
    emissions = emissions.sort_index()

    dataset = capacity.append(emissions)
    dataset = pd.DataFrame(dataset)
    dataset = dataset.transpose()
    dataset.index = naics

    return capacity, emissions, dataset, all_fred, all_epa

#Gets data for the three categories, finds percentage of total energy for sales and gas, and finds monthly average of total energy
def energy_process(category):

    e = ind.EIA_data(category[0])
    s = ind.EIA_data(category[1])
    g = ind.EIA_data(category[2])
    energy = e.getData()
    sales, monthly_sales = s.sumData()
    gas, monthly_gas = g.sumData()

    #Combines gas and sales data, uses only the states in common
    sum = sales.add(gas, fill_value = 0)
    states = set(energy.columns).intersection(set(sum.columns))
    percent = pd.DataFrame(columns = states, index = sum.index)
    percent = percent.sort_index(axis = 1)
    #Finds percentage of total energy not accounted for by sales and gas data
    for year in sum.index:
        for state in states:
            percent.loc[year, state] = sum.loc[year, state] / energy.loc[str(year), state]
    percent_energy = 1 - percent

    monthly_energy = energy.multiply(percent_energy) / 12 #Average total energy not in sales and gas per month
    monthly = monthly_sales.add(monthly_gas, fill_value = 0)
    #Gets total monthly energy
    for dates in monthly.index:
        year = dates.year
        monthly.loc[dates] = monthly.loc[dates].add(monthly_energy.loc[year], fill_value = 0)

    monthly = monthly.drop(monthly.columns[0], axis = 1)
    monthly = monthly.sum(axis = 1) #Combines all states to get national total

    return monthly, percent

def plotData(naics, category):

    capacity, emissions, _, all_fred, _ = process(naics)
    overall_cap = all_fred.iloc[36]
    overall_cap = overall_cap.drop(['Industry', 'Series ID'], axis = 0)
    overall_cap.index = pd.to_datetime(overall_cap.index, format = '%Y%m')
    overall_cap = overall_cap.iloc[84:96] #Data for 2018

    monthly_energy, percent = energy_process(category)
    monthly_energy = monthly_energy.iloc[0:12] #Data for 2018
    monthly_energy = monthly_energy.sort_index()
    percent = percent.iloc[0]
    percent = percent.transpose()

    #make a figure
    plt.figure(figsize=(5,3))
    fig1, ax1 = plt.subplots(2)
    fig1.autofmt_xdate()
    fig1.suptitle('Industrial Output 2011-2018 for NAICS Code %i' %int(naics[0]))

    ax1[0].plot(capacity.index,capacity.values)
    ax1[0].set_title('Capacity Utilization')
    #ax1[0].set_xlabel('Date')
    ax1[0].set_ylabel('Percent of Capacity')

    ax1[1].plot(emissions.index,emissions.values)
    ax1[1].set_title('Reported Emissions')
    ax1[1].set_xlabel('Date')
    ax1[1].set_ylabel('Emissions (kt CO2)')

    fig1.tight_layout()
    plt.savefig("Ind_production.png", dpi=300)

    plt.figure(figsize=(6,3))
    fig2, ax2 = plt.subplots()
    fig2.autofmt_xdate()
    fig2.suptitle('2018 National Industrial Capacity Utilization and Energy Use')

    ax2.scatter(overall_cap.values,monthly_energy.values)
    ax2.set_xlabel('Capacity')
    ax2.set_ylabel('Energy')

    plt.savefig("Ind_cap_energy.png", dpi=300)

    plt.figure(figsize=(25,3))
    fig3, ax3 = plt.subplots()
    fig3.suptitle('2018 Percentage of Energy Use from Electricity and Natural Gas by State')

    #ax3.xaxis.set_major_locator(ticker.MultipleLocator(1))
    ax3.bar(percent.index, percent.values)
    ax3.set_xlabel('State')
    ax3.set_ylabel('Percent of Total Energy')
    plt.xticks(rotation = 90, fontsize = 6)

    plt.savefig("State_sales_gas.png", dpi=300)

    # ax2.plot(overall_cap.index, overall_cap.values, color = 'blue', marker = 'o', label = 'Capacity')
    # ax2.set_xlabel('Date')
    # ax2.set_ylabel('Percent of Capacity')
    #
    # ax3 = ax2.twinx()
    # ax3.plot(monthly_energy.index, monthly_energy.values, color = 'green', marker = 'o', label = 'Energy')
    # ax3.set_ylabel('Energy Consumption (billion Btu)')
    #
    # h1, l1 = ax2.get_legend_handles_labels()
    # h2, l2 = ax3.get_legend_handles_labels()
    # ax2.legend(h1+h2, l1+l2, loc='upper center', ncol=2)

def codecheck(naics):
    #Gets all data in Fred and EPA and checks NAICS codes
    _, _, _, all_fred, all_epa = process(naics)
    #print(all_fred)
    fr_code = all_fred.index.tolist()
    epa_code = all_epa.index.tolist()

    unmatched = []
    for id in epa_code:
         if id not in fr_code and id not in unmatched:
             unmatched.append(id)
    unmatched.sort()
    return unmatched

naics = [311] #Naics code for agriculture
category = [40211,1004,480691] #Category IDs for Total Industrial Energy, Industrial electricity sales, Industrial natural gas consumption
plotData(naics, category)
#print(codecheck(naics))
