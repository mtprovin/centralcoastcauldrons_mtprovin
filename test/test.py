def t1():
    import requests
    from src.api.carts import Customer

    URL = "http://127.0.0.1:8000"
    catalog = requests.get(URL+"/catalog")
    print(catalog)
    #requests.post(URL+"/carts",data={"new_cart": Customer(customer_name="bob")})

if __name__ == "__main__":
    t1()