#from src.api import carts, catalog, bottler, barrels
#
#catalog_ex = [barrels.Barrel(sku=2,ml_per_barrel=20,potion_type=[0,100,0,0],price=60,quantity=2),
#           barrels.Barrel(sku=3,ml_per_barrel=20,potion_type=[0,100,0,0],price=30,quantity=2)]
#plan = barrels.get_wholesale_purchase_plan(catalog_ex)
#barrels.post_deliver_barrels(catalog_ex, 1)
#
#plan = bottler.get_bottle_plan()
#bottler.post_deliver_bottles([bottler.PotionInventory(potion_type=[0,100,0,0],quantity=1)],1)
#
#catalog = catalog.get_catalog()
#
#cart_ex = carts.create_cart()
#carts.set_item_quantity(cart_ex["cart_id"],"GREEN_POTION_0", carts.CartItem(1))
#carts.checkout(cart_ex["cart_id"], carts.CartCheckout('hi'))