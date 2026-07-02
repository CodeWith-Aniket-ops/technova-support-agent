from mcp.server.fastmcp import FastMCP

# Create the TechNova Solutions MCP Server
mcp = FastMCP("TechNova Support Server")

@mcp.tool()
def get_product_details(product_name: str) -> str:
    """Retrieve specifications, price, and warranty details of a TechNova computer hardware product.
    
    Args:
        product_name: Name of the product (e.g. 'TechNova Book 15', 'Apex Keyboard', 'Clarity Monitor').
    """
    products = {
        "technova book 15": "TechNova Book 15 Laptop: Intel Core i7, 16GB RAM, 512GB SSD, 15.6-inch FHD Display. Warranty: 1 year. Price: $999.",
        "technova desktop pro": "TechNova Desktop Pro: AMD Ryzen 7, 32GB RAM, 1TB NVMe SSD, NVIDIA RTX 4060. Warranty: 2 years. Price: $1299.",
        "apex keyboard": "Apex Mechanical Keyboard: RGB Backlit, tactile blue switches, wired USB connection. Warranty: 1 year. Price: $59.",
        "swift mouse": "Swift Wireless Mouse: 16000 DPI, ergonomic grip, rechargeable battery, USB-C. Warranty: 1 year. Price: $39.",
        "clarity monitor": "Clarity 27-inch Monitor: 4K UHD resolution, IPS panel, 144Hz refresh rate, HDMI/DisplayPort. Warranty: 3 years. Price: $349."
    }
    key = product_name.lower().strip()
    return products.get(key, f"Product '{product_name}' not found. TechNova catalog includes: TechNova Book 15, TechNova Desktop Pro, Apex Keyboard, Swift Mouse, Clarity Monitor.")

@mcp.tool()
def check_order_status(order_id: str) -> str:
    """Get the current shipping, processing, or delivery status of a TechNova customer order.
    
    Args:
        order_id: The order ID format: 'TN-XXXXX' where X is a digit.
    """
    statuses = ["Shipped - Out for delivery", "Processing - Preparing for shipment", "Delivered", "Cancelled"]
    idx = sum(ord(c) for c in order_id) % len(statuses)
    status = statuses[idx]
    
    dates = ["July 4, 2026", "July 5, 2026", "July 3, 2026", "N/A"]
    est_date = dates[idx]
    
    return f"Order {order_id} Status: {status}. Estimated/Actual Delivery Date: {est_date}."

@mcp.tool()
def get_warranty_info(category: str) -> str:
    """Retrieve TechNova's standard warranty and replacement terms for a hardware category.
    
    Args:
        category: Hardware category (e.g. 'laptops', 'desktops', 'keyboards', 'mice', 'monitors').
    """
    warranties = {
        "laptops": "Laptops have a 1-year limited warranty covering hardware defects. Accidental damage is not covered.",
        "desktops": "Desktop computers are covered by a 2-year parts and labor warranty.",
        "keyboards": "Keyboards and mice (accessories) are covered by a 1-year replacement warranty.",
        "mice": "Keyboards and mice (accessories) are covered by a 1-year replacement warranty.",
        "monitors": "Monitors are covered by a 3-year warranty against panel defects (dead pixels covering >3 pixels)."
    }
    key = category.lower().strip()
    return warranties.get(key, "For general computer hardware, TechNova provides a standard 1-year manufacturer warranty. Contact palaniket497@gmail.com for details.")

if __name__ == "__main__":
    mcp.run()
