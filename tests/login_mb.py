import mbbank
import datetime
def main():
    username = "0347970961"
    password = ""

    try:
        mb = mbbank.MBBank(username=username, password=password)
        
        # Get balance information
        balance_info = mb.getBalance()
        
        if balance_info.acct_list:
            print(f"Login successful! Found {len(balance_info.acct_list)} account(s).")
            for acct in balance_info.acct_list:
                print(f"Account: {acct.acctNm} {acct.acctNo} - Balance: {acct.currentBalance}")
        else:
            print("Login successful, but no accounts found.")
            
        to_date = datetime.datetime.now()
        from_date = to_date - datetime.timedelta(days=30)

        history = mb.getTransactionAccountHistory(
            accountNo="0347970961", from_date=from_date, to_date=to_date
        )

        if not history.transactionHistoryList:
            print("No transactions found in the last 30 days.")
        else:
            print(f"\nTransaction History ({from_date.date()} to {to_date.date()}):")
            print("-" * 80)
            print(f"{'Date':<20} | {'Amount':<15} | {'Description'}")
            print("-" * 80)
            for transaction in history.transactionHistoryList:
                # Adjust fields based on actual TransactionAccountHistory model if needed
                # Assuming fields based on common banking API structures and typical usage
                # If 'transactionDate' or similar exists, use it.
                # Printing the raw object or available fields if unsure, but let's try to be specific based on typical mbbank usage.
                # Since I can't see the exact model definition for TransactionAccountHistory in the outline (it was truncated or in a modal file),
                # I will rely on the fact that it returns a list of transactions.
                # Let's try to print a few likely fields.

                date = getattr(transaction, "transactionDate", "N/A")
                amount = getattr(transaction, "creditAmount", 0) or getattr(
                    transaction, "debitAmount", 0
                )
                description = getattr(transaction, "description", "No description")

                print(f"{str(date):<20} | {str(amount):<15} | {description}")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
