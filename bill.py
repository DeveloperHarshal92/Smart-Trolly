import pandas as pd

# Products and their prices
products = {'dairy_milk': 5, 'colgate': 20, 'good_day': 10, 'parle_g': 10, 'parachute': 15}

def generateBill(items_list):
    # Scanned items list
    #items_list = ['dairy_milk', 'colgate', 'dairy_milk', 'colgate', 'good_day', 'parle_g', 'parachute', 'parle_g']

    # Calculate the bill and total cost
    bill_data = []
    unique_items = set(items_list)
    total_bill = 0

    for i, item in enumerate(unique_items, start=1):
        quantity = items_list.count(item)
        unit_price = products[item]
        total_price = quantity * unit_price
        total_bill += total_price
        bill_data.append([i, item, quantity, unit_price, total_price])

    # Create the dataframe
    bill_df = pd.DataFrame(bill_data, columns=["SN", "Item", "Quantity", "Unit Price", "Total"])

    # Append the total bill row
    bill_df.loc[len(bill_df)] = ["", "Total", "", "", total_bill]

    print(bill_df)
    return(bill_df,total_bill)
