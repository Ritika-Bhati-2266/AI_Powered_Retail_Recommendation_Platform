"""
Seed data generator for the retail hyper-personalisation engine demo.
Generates realistic synthetic customers, products, events, and initial segments.
"""
import hashlib
import logging
import random
import uuid
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import Customer, CustomerSegment, Event, Product
from app.security import hash_password
from app.utils import utcnow

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────

FIRST_NAMES = [
    "Olivia", "Liam", "Emma", "Noah", "Amelia", "Oliver", "Sophia", "Elijah",
    "Isabella", "Mateo", "Mia", "Lucas", "Charlotte", "Levi", "Luna", "Ezra",
    "Harper", "Asher", "Evelyn", "Leo", "Aria", "James", "Ella", "Ethan",
    "Avery", "Benjamin", "Scarlett", "Sebastian", "Grace", "Henry", "Chloe",
    "Muhammad", "Layla", "Jack", "Riley", "Owen", "Zoey", "Daniel", "Nora",
    "Aiden", "Lily", "Samuel", "Eleanor", "Ryan", "Hannah", "Wyatt", "Addison",
    "Carter", "Aubrey", "John", "Ellie", "Luke", "Stella", "Julian", "Natalie",
    "David", "Savannah", "Anthony", "Leah", "Ivan", "Aaliyah", "Nathan", "Skylar",
    "Dylan", "Maya", "Caleb", "Paisley", "Andrew", "Audrey", "Isaac", "Naomi",
    "Thomas", "Kinsley", "Christian", "Aurora", "Gabriel", "Bella", "Theodore",
    "Genesis", "Josiah", "Ariana", "Adrian", "Valentina", "Alex", "Mackenzie",
    "Christopher", "Eva", "Lincoln", "Elena", "Grayson", "Alice", "Ayden", "Sofia",
    "Parker", "Claire", "Cooper", "Sadie", "Santiago", "Caroline",
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
    "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez",
    "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin",
    "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark",
    "Ramirez", "Lewis", "Robinson", "Walker", "Young", "Allen", "King",
    "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores", "Green",
    "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell", "Mitchell",
    "Carter", "Roberts", "Gomez", "Phillips", "Evans", "Turner", "Diaz",
    "Patel", "Cruz", "Richards", "Edwards", "Collins", "Chavez", "Stewart",
    "Morris", "Murphy", "Cook", "Rogers", "Morgan", "Peterson", "Cooper",
    "Reed", "Bailey", "Bell", "Gomez", "Kelly", "Howard", "Ward", "Cox",
    "Diaz", "Richardson", "Wood", "Watson", "Brooks", "Bennett", "Gray",
    "James", "Reyes", "Cruz", "Hughes", "Price", "Myers", "Long",
    "Foster", "Sanders", "Ross", "Morales", "Powell", "Sullivan", "Russell",
]

CATEGORIES = {
    "Electronics": ["Smartphones", "Laptops", "Headphones", "Tablets", "Smartwatches", "Cameras", "Cables & Chargers", "Speakers"],
    "Clothing": ["T-Shirts", "Jeans", "Jackets", "Dresses", "Shoes", "Sneakers", "Socks", "Activewear"],
    "Home & Kitchen": ["Cookware", "Furniture", "Appliances", "Bedding", "Decor", "Lighting", "Cleaning Supplies", "Storage & Organization"],
    "Books": ["Fiction", "Non-Fiction", "Science", "History", "Self-Help", "Children's Books", "Comics"],
    "Sports & Outdoors": ["Fitness Equipment", "Sportswear", "Yoga", "Cycling", "Camping Gear", "Water Bottles", "Gym Bags"],
    "Beauty & Personal Care": ["Skincare", "Makeup", "Haircare", "Fragrance", "Bath & Body", "Grooming", "Sunscreen"],
    "Toys & Games": ["Board Games", "Puzzles", "Action Figures", "Building Sets", "Educational Toys", "Outdoor Play", "Video Games"],
    "Grocery & Gourmet": ["Snacks", "Beverages", "Pantry Staples", "Organic Foods", "Coffee & Tea", "Chocolates", "International Foods"],
    "Automotive": ["Car Accessories", "Car Electronics", "Cleaning & Detailing", "Oils & Fluids", "Interior Accessories", "Exterior Accessories", "Car Care Kits"],
    "Pet Supplies": ["Dog Food", "Cat Food", "Pet Toys", "Pet Beds", "Pet Grooming", "Pet Accessories"],
    "Office & Stationery": ["Desks & Chairs", "Notebooks & Pens", "Printers & Supplies", "Organization", "School Supplies", "Art Supplies"],
    "Baby & Kids": ["Diapers & Wipes", "Baby Gear", "Nursery", "Baby Clothing", "Kids Toys", "Feeding"],
    "Health & Wellness": ["Vitamins & Supplements", "First Aid", "Essential Oils", "Massage & Relaxation", "Fitness Trackers", "Wellness"],
    "Music & Media": ["Musical Instruments", "Vinyl & CDs", "Streaming Devices", "Karaoke", "DJ Equipment"],
}

BRANDS_BY_CATEGORY = {
    "Electronics": ["TechPro", "ElectroMax", "DigiLife", "SmartWave", "NovaTech", "FusionX", "SonicTech", "PowerGear"],
    "Clothing": ["FashionFirst", "UrbanStyle", "ClassicWear", "TrendyFit", "LuxeThreads", "VibeApparel", "StreetEdge", "ComfortCore"],
    "Home & Kitchen": ["HomeSweet", "KitchenPro", "LivingWell", "ComfortHome", "EliteLiving", "CozyNest", "HomeChef", "Organiza"],
    "Books": ["PageTurner", "ReadWise", "BookHaven", "LitWorld", "NovelNest", "BrainFuel", "StoryCraft", "PaperTrail"],
    "Sports & Outdoors": ["FitLife", "SportMax", "ActiveGear", "EndurancePro", "PeakPerformance", "IronWill", "TrailBlazer", "SummitGear"],
    "Beauty & Personal Care": ["GlowUp", "PureBeauty", "RadianceCo", "NaturalGlow", "LuxeLook", "FreshFace", "BloomCare", "EssenceLab"],
    "Toys & Games": ["FunFactory", "PlayWorld", "ToyChest", "KidJoy", "ImagiNation", "HappyPlay", "GameOn", "BuildMaster"],
    "Grocery & Gourmet": ["FreshFarm", "NatureBest", "DailyGoods", "PureHarvest", "GreenChoice", "SmartShop", "TasteTrail", "OrganicValley"],
    "Automotive": ["AutoPro", "DriveGear", "CarCare", "RoadMaster", "TurboFit", "ShieldAuto", "MotoZone", "GearHead"],
    "Pet Supplies": ["PetJoy", "HappyPaws", "FurryFriends", "PetCare", "AnimalLodge", "PurrfectPet", "WildTails", "PetNest"],
    "Office & Stationery": ["WorkSpace", "OfficePro", "StationeryKing", "DeskMate", "PaperPlus", "OrganizedLife", "WriteWell", "ArtisanCraft"],
    "Baby & Kids": ["BabyJoy", "LittleStars", "TinyTot", "NurtureBaby", "KiddoZone", "SweetSlumber", "BabyBloom", "ParentPick"],
    "Health & Wellness": ["VitalLife", "WellnessPlus", "NatureCure", "PureHealth", "ActiveLife", "HolisticCare", "NutriBest", "ZenMed"],
    "Music & Media": ["SoundWave", "MelodyPro", "TuneCraft", "BeatStreet", "AudioPhile", "RhythmHouse", "StageMaster", "ChordVibe"],
}

# ── Explicit Product Definitions ──────────────────────────────────────────────
# Each entry: (brand, descriptive_name, price_in_usd)
# The final product name is "Brand DescriptiveName" for realistic search results.

PRODUCT_DEFINITIONS: dict[str, dict[str, list[tuple[str, str, float]]]] = {
    "Electronics": {
        "Smartphones": [
            ("TechPro", "Apex Pro 5G Smartphone 256GB OLED Display", 899.99),
            ("ElectroMax", "Lumina XR 5G Unlocked Smartphone 128GB", 749.99),
            ("DigiLife", "Nova 15 Pro Max 256GB Triple Camera", 1099.99),
            ("SmartWave", "Pulse S24 Ultra 5G Smartphone with S Pen", 1199.99),
            ("NovaTech", "Stellar X 5G Smartphone 512GB", 999.99),
            ("FusionX", "Merge Pro 5G Foldable Smartphone", 1399.99),
            ("SonicTech", "Echo 5G Smartphone 128GB Water Resistant", 699.99),
            ("PowerGear", "Volt X80 5G Rugged Smartphone 256GB", 799.99),
        ],
        "Laptops": [
            ("TechPro", "UltraBook 15 Pro Laptop Intel i7 16GB RAM 512GB SSD", 1299.99),
            ("ElectroMax", "WorkStation 14 Business Laptop i5 8GB 256GB", 849.99),
            ("DigiLife", "Creator 16 Laptop Intel i9 32GB RAM 1TB SSD", 1899.99),
            ("SmartWave", "SwiftBook Air M3 Laptop 13-inch 16GB 512GB", 1499.99),
            ("NovaTech", "Gamer X17 Gaming Laptop RTX 4070 32GB RAM", 2199.99),
            ("FusionX", "Convert 14 2-in-1 Touchscreen Laptop i7 16GB", 1099.99),
            ("SonicTech", "SlimNote 15 Laptop AMD Ryzen 7 16GB 512GB", 949.99),
            ("PowerGear", "RuggedBook Pro Waterproof Laptop 14-inch", 1599.99),
        ],
        "Headphones": [
            ("TechPro", "Sonic Pro Wireless Noise Cancelling Headphones Black", 349.99),
            ("ElectroMax", "BassBoost Over-Ear Bluetooth Headphones 40hr Battery", 199.99),
            ("DigiLife", "Studio HD Wired Monitor Headphones for Professionals", 299.99),
            ("SmartWave", "AirPods Pro True Wireless Earbuds Noise Cancelling", 249.99),
            ("NovaTech", "SportFit Wireless Earbuds IPX7 Waterproof 30hr", 129.99),
            ("FusionX", "Comfort 900 ANC Over-Ear Headphones with Case", 279.99),
            ("SonicTech", "ClipOn Wireless Earbuds Ultra Lightweight", 89.99),
            ("PowerGear", "Gamer X5 Surround Sound Gaming Headset RGB", 159.99),
        ],
        "Tablets": [
            ("TechPro", "Tab S9 Ultra 14.6-inch Tablet 256GB Wi-Fi 6E", 999.99),
            ("ElectroMax", "Pad Pro 12.9 M3 Chip Tablet 256GB with Pen Support", 1099.99),
            ("DigiLife", "Tab 11 Pro 11-inch Android Tablet 128GB", 349.99),
            ("SmartWave", "PulseTab 10 OLED Entertainment Tablet 64GB", 279.99),
            ("NovaTech", "SketchPad Pro Drawing Tablet with Stylus 13-inch", 599.99),
            ("FusionX", "MergeTab 12 2-in-1 Tablet with Detachable Keyboard", 449.99),
            ("SonicTech", "EchoTab 8 Kids Edition Tablet Parental Controls", 199.99),
            ("PowerGear", "RuggedTab 10 Waterproof Dustproof Tablet 64GB", 499.99),
        ],
        "Smartwatches": [
            ("TechPro", "Watch X Pro Ultra Fitness Smartwatch GPS AMOLED", 449.99),
            ("ElectroMax", "Vibe Watch 8 45mm Stainless Steel Smartwatch", 399.99),
            ("DigiLife", "FitSphere Pro Health Smartwatch Blood Oxygen Monitor", 249.99),
            ("SmartWave", "Pulse Watch SE GPS Sports Smartwatch 40mm", 279.99),
            ("NovaTech", "Stellar Watch 3 46mm Titanium Smartwatch 7-Day Battery", 349.99),
            ("FusionX", "Merge Watch Active Waterproof Smartwatch 50m", 199.99),
            ("SonicTech", "Echo Smart Ring Health Tracker Sleep Monitor", 299.99),
            ("PowerGear", "Rugged Watch Outdoor GPS Smartwatch Compass Altimeter", 379.99),
        ],
        "Cameras": [
            ("TechPro", "DSLR Pro X 24.2MP Digital Camera with 18-55mm Lens", 799.99),
            ("ElectroMax", "MirrorLess 4K 20.1MP Compact System Camera Body Only", 649.99),
            ("DigiLife", "ActionCam 5 Waterproof Sports Camera 4K60fps", 399.99),
            ("SmartWave", "PocketCam Instant Digital Camera with Photo Printer", 149.99),
            ("NovaTech", "ZoomShot 50x Optical Zoom Bridge Camera 20MP", 549.99),
            ("FusionX", "Merge 360 360-Degree VR Camera 5.7K Video", 499.99),
            ("SonicTech", "DashCam Pro 4K Car Dashboard Camera Night Vision GPS", 179.99),
            ("PowerGear", "TrailCam X Wildlife Camera 20MP Night Vision", 249.99),
        ],
        "Cables & Chargers": [
            ("TechPro", "USB-C to Lightning Cable 6ft Braided Fast Charging", 19.99),
            ("ElectroMax", "100W USB-C Charger GaN Tech Compact Wall Charger", 49.99),
            ("DigiLife", "MagSafe Wireless Charging Pad 15W Fast Charge", 39.99),
            ("SmartWave", "USB-C to USB-C Cable 10ft 240W PD Charging Cable Braided", 24.99),
            ("NovaTech", "Power Bank 20000mAh Portable Charger PD 65W", 59.99),
            ("FusionX", "Multi Charging Station Desktop Organizer 6 Devices", 44.99),
            ("SonicTech", "HDMI Cable 4K 6ft High Speed HDMI 2.1 Cord", 14.99),
            ("PowerGear", "Car Charger USB-C 45W Fast Charger Adapter Vehicle", 29.99),
        ],
        "Speakers": [
            ("TechPro", "SoundBlast Pro Portable Bluetooth Speaker 50W Bass", 179.99),
            ("ElectroMax", "HomePod Mini Smart Speaker with Voice Assistant", 99.99),
            ("DigiLife", "SoundBar 2.1 Channel Home Theater System with Subwoofer", 299.99),
            ("SmartWave", "PulseBeat Waterproof Bluetooth Speaker IP67 24hr", 69.99),
            ("NovaTech", "Tower Speaker 5.1 Surround Sound System Floor Standing", 499.99),
            ("FusionX", "PartyBox 300W Portable Party Speaker Bluetooth Mic Input", 349.99),
            ("SonicTech", "Mini Portable Bluetooth Speaker Clip-On Design 10W", 39.99),
            ("PowerGear", "Outdoor Rock Speaker 100W Weatherproof Garden Audio", 199.99),
        ],
    },
    "Clothing": {
        "T-Shirts": [
            ("FashionFirst", "Premium Cotton Crew Neck T-Shirt Regular Fit White", 29.99),
            ("UrbanStyle", "Graphic Print Oversized T-Shirt Streetwear Black", 34.99),
            ("ClassicWear", "Linen Blend Casual T-Shirt Slim Fit Navy Blue", 39.99),
            ("TrendyFit", "Performance Dry-Fit Athletic T-Shirt Moisture Wicking", 24.99),
            ("LuxeThreads", "Organic Cotton Crew T-Shirt Sustainable Soft Touch", 44.99),
            ("VibeApparel", "Vintage Washed Logo T-Shirt Relaxed Fit Grey", 32.99),
            ("StreetEdge", "Striped Polo T-Shirt Cotton Blend Collared", 36.99),
            ("ComfortCore", "Henley Long Sleeve T-Shirt Button Placket Cotton", 42.99),
        ],
        "Jeans": [
            ("FashionFirst", "Slim Fit Stretch Jeans Dark Wash 5-Pocket Denim", 69.99),
            ("UrbanStyle", "Straight Leg Denim Jeans Mid-Rise Classic Blue", 64.99),
            ("ClassicWear", "Bootcut Jeans Relaxed Fit Cotton Stretch Dark Wash", 59.99),
            ("TrendyFit", "Skinny Jeans Super Stretch High-Rise Black Denim", 74.99),
            ("LuxeThreads", "Selvedge Raw Denim Jeans Premium Quality Unwashed", 129.99),
            ("VibeApparel", "Distressed Ripped Jeans Slim Tapered Light Wash", 79.99),
            ("StreetEdge", "Cargo Jeans Multi-Pocket Relaxed Fit Utility Style", 89.99),
            ("ComfortCore", "Elastic Waist Relaxed Jeans Comfort Stretch Casual", 54.99),
        ],
        "Jackets": [
            ("FashionFirst", "Leather Biker Jacket Genuine Leather Regular Fit Black", 249.99),
            ("UrbanStyle", "Puffer Jacket Down Fill Hooded Warm Winter Insulated", 179.99),
            ("ClassicWear", "Denim Trucker Jacket Classic Blue Cotton Button Front", 89.99),
            ("TrendyFit", "Windbreaker Waterproof Running Jacket Lightweight Packable", 69.99),
            ("LuxeThreads", "Wool Blend Blazer Jacket Slim Fit Notch Lapel Charcoal", 199.99),
            ("VibeApparel", "Bomber Jacket Satin Finish Zip Front Casual Style Green", 119.99),
            ("StreetEdge", "Hooded Parka Water-Resistant Winter Coat Faux Fur Trim", 229.99),
            ("ComfortCore", "Fleece Zip-Up Jacket Soft Warm Mid-Layer Outdoor", 59.99),
        ],
        "Dresses": [
            ("FashionFirst", "Floral Maxi Dress Flowy Bohemian Print V-Neck", 79.99),
            ("UrbanStyle", "Bodycon Midi Dress Stretch Fit Cocktail Party Black", 59.99),
            ("ClassicWear", "A-Line Mini Dress Cotton Blend Fit-and-Flare Navy", 54.99),
            ("TrendyFit", "Sleeveless Shift Dress Work Office Professional Knee-Length", 69.99),
            ("LuxeThreads", "Silk Evening Gown Formal Long Dress Elegant Satin Red", 299.99),
            ("VibeApparel", "Wrap Dress Flattering V-Neck Tie Waist Printed Midi", 74.99),
            ("StreetEdge", "Denim Shirt Dress Button Front Casual Street Style", 84.99),
            ("ComfortCore", "Knit Sweater Dress Long Sleeve Cozy Winter Casual", 64.99),
        ],
        "Shoes": [
            ("FashionFirst", "Leather Loafers Comfort Slip-On Dress Shoes Brown", 119.99),
            ("UrbanStyle", "Casual Canvas Shoes Low Top Lace-Up Everyday Wear", 49.99),
            ("ClassicWear", "Oxford Leather Dress Shoes Cap-Toe Formal Business Black", 149.99),
            ("TrendyFit", "Hiking Boots Waterproof Ankle High Outdoor Trail", 139.99),
            ("LuxeThreads", "Premium Leather Boots Chelsea Ankle Pull-On Tan", 199.99),
            ("VibeApparel", "Sandals Slide Flat Cushioned Footbed Summer Beach", 39.99),
            ("StreetEdge", "High Top Fashion Sneakers Platform Chunky Sole White", 99.99),
            ("ComfortCore", "Walking Shoes Mesh Breathable Slip-On Orthopedic", 89.99),
        ],
        "Sneakers": [
            ("FashionFirst", "Running Sneakers Lightweight Cushioned Sole Performance White", 129.99),
            ("UrbanStyle", "Basketball High Top Sneakers Padded Ankle Support Black", 159.99),
            ("ClassicWear", "Retro Court Classic Sneakers Vintage Style Leather White", 89.99),
            ("TrendyFit", "Cross Training Sneakers Multi-Sport Gym Workout Grey", 109.99),
            ("LuxeThreads", "Designer Low Top Sneakers Premium Leather Gold Accents", 249.99),
            ("VibeApparel", "Fashion Running Sneakers Chunky Sole Retro Style Pink", 119.99),
            ("StreetEdge", "Skateboarding Sneakers Suede Canvas Flat Sole Classic", 74.99),
            ("ComfortCore", "Walking Sneakers Slip-On Memory Foam Arch Support", 94.99),
        ],
        "Socks": [
            ("FashionFirst", "Dress Socks Cotton Blend Formal Business Ankle Length Multi Pack", 19.99),
            ("UrbanStyle", "Athletic Cushioned Socks Crew Length Moisture Wicking 6-Pack", 24.99),
            ("ClassicWear", "Merino Wool Hiking Socks Thermal Cushion Mid-Calf Pair", 16.99),
            ("TrendyFit", "No-Show Invisible Socks Silicone Grip Loafers Flats 6-Pack", 14.99),
            ("LuxeThreads", "Cashmere Blend Lounge Socks Luxury Soft Warm Gift Set", 39.99),
            ("VibeApparel", "Compression Socks Graduated Support Travel Running Knee High", 21.99),
            ("StreetEdge", "Colorful Patterned Novelty Socks Fun Designs Crew 5-Pack", 17.99),
            ("ComfortCore", "Thermal Winter Socks Fleece Lined Extra Warm Boot Socks", 22.99),
        ],
        "Activewear": [
            ("FashionFirst", "Leggings High-Waist Compression Yoga Pants Moisture Wicking Black", 49.99),
            ("UrbanStyle", "Gym Joggers Tapered Fit Fleece Sweatpants Zip Pockets Grey", 44.99),
            ("ClassicWear", "Sports Bra High Support Medium Impact Racerback Black", 39.99),
            ("TrendyFit", "Running Shorts 2-in-1 Compression Liner Quick Dry 5-Inch", 34.99),
            ("LuxeThreads", "Yoga Top Racerback Tank Breathable Stretch Fabric", 32.99),
            ("VibeApparel", "Training Hoodie Lightweight Zip-Up Athletic Performance", 59.99),
            ("StreetEdge", "Swim Trunks Quick Dry Board Shorts with Mesh Lining", 37.99),
            ("ComfortCore", "Base Layer Thermal Top Long Sleeve Moisture Wicking", 29.99),
        ],
    },
    "Home & Kitchen": {
        "Cookware": [
            ("HomeSweet", "Non-Stick Fry Pan Set 3-Piece Titanium Coated Kitchen", 79.99),
            ("KitchenPro", "Stainless Steel Cookware Set 10-Piece Pots and Pans", 199.99),
            ("LivingWell", "Cast Iron Dutch Oven 6-Quart Enamel Coated Heavy Duty", 89.99),
            ("ComfortHome", "Ceramic Non-Stick Baking Sheet Set 2-Piece Oven Tray", 44.99),
            ("EliteLiving", "Chef Knife 8-Inch Professional Kitchen Blade Stainless", 69.99),
            ("CozyNest", "Cutting Board Set Bamboo 3-Piece Wood Kitchen Chopping", 34.99),
            ("HomeChef", "Pressure Cooker 8-Quart Electric Multi-Cooker Stainless Steel", 119.99),
            ("Organiza", "Kitchen Utensil Set Silicone 12-Piece Heat Resistant", 29.99),
        ],
        "Furniture": [
            ("HomeSweet", "Sofa 3-Seater Fabric Upholstered Couch with Pillows Beige", 699.99),
            ("KitchenPro", "Dining Table 6-Seater Solid Wood Rectangular Kitchen Table", 549.99),
            ("LivingWell", "Bookshelf 5-Tier Tall Storage Shelf Unit Black Wood", 149.99),
            ("ComfortHome", "Bed Frame Queen Size Platform Upholstered Headboard Beige", 399.99),
            ("EliteLiving", "Office Desk Standing Adjustable Height Electric Sit-Stand", 449.99),
            ("CozyNest", "Coffee Table Round Glass Top Metal Base Living Room", 199.99),
            ("HomeChef", "Kitchen Island Cart with Butcher Block Top Storage Rack", 279.99),
            ("Organiza", "Shoe Rack Entryway Storage Bench 2-Tier Bamboo", 89.99),
        ],
        "Appliances": [
            ("HomeSweet", "Refrigerator French Door 25 cu ft Smart Fridge Ice Maker", 1899.99),
            ("KitchenPro", "Microwave Oven Countertop 1.2 cu ft 1200W Stainless Steel", 149.99),
            ("LivingWell", "Air Fryer 6-Quart Digital Hot Oven Oil-Free Cooking Black", 89.99),
            ("ComfortHome", "Robot Vacuum Smart Mapping Self-Charging Wi-Fi Connected", 399.99),
            ("EliteLiving", "Coffee Maker 12-Cup Programmable Drip Brewer Thermal Carafe", 79.99),
            ("CozyNest", "Portable Air Conditioner 10000 BTU Windowless Cooler Fan", 449.99),
            ("HomeChef", "Stand Mixer 5.5-Quart 660W Tilt-Head Kitchen Mixer White", 349.99),
            ("Organiza", "Food Processor 14-Cup 720W Vegetable Chopper Slicer", 129.99),
        ],
        "Bedding": [
            ("HomeSweet", "Comforter Set Queen Size 7-Piece Bed-in-a-Bag White", 89.99),
            ("KitchenPro", "Pillow Set King Size Down Alternative Hypoallergenic 2-Pack", 49.99),
            ("LivingWell", "Sheet Set Queen 100% Egyptian Cotton 800 Thread Count 4-Piece", 79.99),
            ("ComfortHome", "Mattress Topper Queen 3-Inch Gel Memory Foam Cooling", 129.99),
            ("EliteLiving", "Duvet Cover Queen Size White Cotton 3-Piece with Zipper", 59.99),
            ("CozyNest", "Throw Blanket Soft Fleece Super Plush Cozy Couch Blanket 50x70", 34.99),
            ("HomeChef", "Weighted Blanket 15lbs Queen Size Glass Beads Grey", 89.99),
            ("Organiza", "Pillow Protectors Waterproof Zippered Queen 2-Pack", 24.99),
        ],
        "Decor": [
            ("HomeSweet", "Wall Art Canvas Framed Abstract Painting 3-Piece Set", 69.99),
            ("KitchenPro", "Table Lamp Modern LED Bedside Desk Lamp Touch Dimmer", 45.99),
            ("LivingWell", "Area Rug 5x7 ft Indoor Soft Shaggy Carpet Living Room Grey", 99.99),
            ("ComfortHome", "Throw Pillow Cushion Set 4-Pack Decorative Square Linen", 39.99),
            ("EliteLiving", "Floor Vase Tall 24-Inch Ceramic Decorative Vessel White", 59.99),
            ("CozyNest", "Artificial Monstera Plant 4-Foot Fake Tree in Pot Indoor", 44.99),
            ("HomeChef", "Wall Clock Large 24-Inch Modern Silent Battery Operated", 34.99),
            ("Organiza", "Photo Frame Collage Set 10-Pack Wall Gallery Display", 29.99),
        ],
        "Lighting": [
            ("HomeSweet", "Floor Lamp LED Torchiere 1500 Lumens Dimmable Black", 79.99),
            ("KitchenPro", "Pendant Light Kitchen Island Modern Linear Hanging 4-Light", 149.99),
            ("LivingWell", "Ceiling Fan with Light 52-Inch Remote Control Flush Mount", 199.99),
            ("ComfortHome", "Desk Lamp LED Architect Clamp-On Swing Arm Adjustable", 59.99),
            ("EliteLiving", "Chandelier Crystal 6-Light Dimmable Entryway Foyer Gold", 249.99),
            ("CozyNest", "Night Light Plug-in Motion Sensor LED Auto Dimming", 14.99),
            ("HomeChef", "LED Strip Lights 32.8ft RGB Color Changing Smart App Control", 29.99),
            ("Organiza", "Bathroom Vanity Light Bar 3-Light Chrome Glass Shade", 89.99),
        ],
        "Cleaning Supplies": [
            ("HomeSweet", "Vacuum Cleaner Cordless Stick Lightweight Powerful Suction", 299.99),
            ("KitchenPro", "Mop and Bucket Set Spin Dry Mop System with Wringer", 44.99),
            ("LivingWell", "Broom and Dustpan Set Indoor Outdoor Heavy Duty", 24.99),
            ("ComfortHome", "All-Purpose Cleaner Multi-Surface Spray 32oz 3-Pack", 18.99),
            ("EliteLiving", "Steam Mop Floor Cleaner Handheld Steam Cleaner Multi-Purpose", 79.99),
            ("CozyNest", "Microfiber Cleaning Cloths 24-Pack Lint Free Streak Free", 16.99),
            ("HomeChef", "Trash Can 13-Gallon Stainless Steel Step Open Kitchen", 59.99),
            ("Organiza", "Laundry Basket Hamper Woven Rope Collapsible 2-Tier", 34.99),
        ],
        "Storage & Organization": [
            ("HomeSweet", "Storage Bins Set 6-Pack Plastic Stackable with Lids Clear", 39.99),
            ("KitchenPro", "Closet Organizer System 12-Cube DIY Modular Shelving Unit", 89.99),
            ("LivingWell", "Drawer Organizer Set 10-Piece Adjustable Dividers Cabinet", 24.99),
            ("ComfortHome", "Under Bed Storage Bags 2-Pack Zippered Heavy Duty 90L", 34.99),
            ("EliteLiving", "Jewelry Box Organizer Large Velvet Layered Necklace Earring Case", 49.99),
            ("CozyNest", "Over the Door Organizer 24-Pocket Hanging Storage Clear", 19.99),
            ("HomeChef", "Spice Rack Wall Mount 2-Tier Magnetic Stainless Steel", 29.99),
            ("Organiza", "Garage Storage Shelf Heavy Duty Steel 4-Tier Adjustable", 119.99),
        ],
    },
    "Books": {
        "Fiction": [
            ("PageTurner", "The Midnight Library A Novel Bestseller Hardcover", 24.99),
            ("ReadWise", "Tomorrow and Tomorrow and Tomorrow Literary Fiction", 27.99),
            ("BookHaven", "The Covenant of Water Epic Family Saga Historical", 29.99),
            ("LitWorld", "Yellowface Satire Contemporary Fiction Thriller", 26.99),
            ("NovelNest", "Lessons in Chemistry Science Fiction Period Drama", 25.99),
            ("BrainFuel", "The Bee Sting Pulitzer Prize Winning Fiction", 28.99),
            ("StoryCraft", "North Woods Nature Fiction Multi-Generational Epic", 24.99),
            ("PaperTrail", "The Fraud Historical Fiction Victorian London Mystery", 27.99),
        ],
        "Non-Fiction": [
            ("PageTurner", "Atomic Habits Tiny Changes Remarkable Results Self-Improvement", 18.99),
            ("ReadWise", "The Body Keeps the Score Brain Mind Body Healing Trauma", 19.99),
            ("BookHaven", "Sapiens A Brief History of Humankind Hardcover", 22.99),
            ("LitWorld", "Educated A Memoir Overcoming Adversity Bestseller", 16.99),
            ("NovelNest", "Outliers The Story of Success Malcolm Gladwell", 17.99),
            ("BrainFuel", "Thinking Fast and Slow Psychology Behavioral Economics", 20.99),
            ("StoryCraft", "In Cold Blood True Crime Classic Non-Fiction Narrative", 18.99),
            ("PaperTrail", "Becoming Michelle Obama Autobiography Memoir", 19.99),
        ],
        "Science": [
            ("PageTurner", "A Brief History of Time Stephen Hawking Physics Cosmology", 16.99),
            ("ReadWise", "The Selfish Gene Evolutionary Biology Richard Dawkins", 15.99),
            ("BookHaven", "Cosmos Carl Sagan Illustrated Space Exploration Science", 24.99),
            ("LitWorld", "The Gene An Intimate History Genetics Inheritance Medicine", 18.99),
            ("NovelNest", "Astrophysics for People in a Hurry Neil deGrasse Tyson", 14.99),
            ("BrainFuel", "Silent Spring Environmental Science Rachel Carson Classic", 16.99),
            ("StoryCraft", "The Sixth Extinction An Unnatural History Climate Change", 17.99),
            ("PaperTrail", "The Immortal Life of Henrietta Lacks Medical Ethics Bioethics", 15.99),
        ],
        "History": [
            ("PageTurner", "The Guns of August World War I History Classic Military", 19.99),
            ("ReadWise", "SPQR A History of Ancient Rome Mary Beard Hardcover", 22.99),
            ("BookHaven", "The Wright Brothers Biographical History Aviation Invention", 18.99),
            ("LitWorld", "1776 American Revolution Founding Fathers David McCullough", 20.99),
            ("NovelNest", "The Diary of a Young Girl Anne Frank World War II Memoir", 14.99),
            ("BrainFuel", "Genghis Khan and the Making of the Modern World Mongolian Empire", 17.99),
            ("StoryCraft", "The Silk Roads A New History of the World Peter Frankopan", 21.99),
            ("PaperTrail", "Team of Rivals Lincoln Political Genius Civil War History", 24.99),
        ],
        "Self-Help": [
            ("PageTurner", "The 7 Habits of Highly Effective People Personal Development", 17.99),
            ("ReadWise", "How to Win Friends and Influence People Dale Carnegie Classic", 14.99),
            ("BookHaven", "The Power of Now Spiritual Enlightenment Eckhart Tolle", 15.99),
            ("LitWorld", "Daring Greatly Courage Vulnerability Brene Brown", 16.99),
            ("NovelNest", "Man Search for Meaning Viktor Frankl Psychology Philosophy", 13.99),
            ("BrainFuel", "The Subtle Art of Not Giving a Fck Counterintuitive Living", 18.99),
            ("StoryCraft", "Think and Grow Rich Napoleon Hill Success Philosophy", 12.99),
            ("PaperTrail", "You Are a Badass How to Stop Doubting Greatness Live Life", 16.99),
        ],
        "Children's Books": [
            ("PageTurner", "The Very Hungry Caterpillar Board Book Classic Baby Toddler", 12.99),
            ("ReadWise", "Goodnight Moon Bedtime Story Board Book Children Classic", 10.99),
            ("BookHaven", "Where the Wild Things Are Maurice Sendak Picture Book", 14.99),
            ("LitWorld", "The Cat in the Hat Dr Seuss Beginner Book Classic Rhyming", 13.99),
            ("NovelNest", "Harry Potter and the Sorcerer's Stone Illustrated Edition", 29.99),
            ("BrainFuel", "The Wonderful Wizard of Oz Complete Original Story Classic", 11.99),
            ("StoryCraft", "Oh the Places You'll Go Dr Seuss Graduation Gift Book", 15.99),
            ("PaperTrail", "Charlotte's Web E.B. White Classic Children Literature", 9.99),
        ],
        "Comics": [
            ("PageTurner", "Watchmen Alan Moore Graphic Novel DC Comics Superhero", 24.99),
            ("ReadWise", "Maus Art Spiegelman Holocaust Survivor Tale Pulitzer Winner", 18.99),
            ("BookHaven", "Saga Volume 1 Brian K Vaughan Space Fantasy Epic Comic", 12.99),
            ("LitWorld", "Batman The Killing Joke DC Comics Graphic Novel Alan Moore", 16.99),
            ("NovelNest", "Persepolis Marjane Satrapi Coming of Age Iran Revolution", 15.99),
            ("BrainFuel", "Spider-Man Across the Spider-Verse Movie Adaptation Comic", 17.99),
            ("StoryCraft", "Sandman Vol 1 Preludes Nocturnes Neil Gaiman Dream Comic", 19.99),
            ("PaperTrail", "Hellboy Seed of Destruction Mike Mignola Dark Horse Comics", 18.99),
        ],
    },
    "Sports & Outdoors": {
        "Fitness Equipment": [
            ("FitLife", "Adjustable Dumbbell Set 5-52.5lbs Pair Quick Change Weight", 349.99),
            ("SportMax", "Treadmill Folding Compact Home Running Machine Incline", 799.99),
            ("ActiveGear", "Jump Rope Speed Cable Adjustable Ball Bearing Cardio Fitness", 19.99),
            ("EndurancePro", "Resistance Bands Set 5-Level Exercise Band Door Anchor", 29.99),
            ("PeakPerformance", "Yoga Mat Premium Non-Slip Eco Friendly 6mm Thick Exercise", 49.99),
            ("IronWill", "Kettlebell Set 10-40lbs Cast Iron Hand Weight Pair", 159.99),
            ("TrailBlazer", "Pull Up Bar Doorway Chin Up Bar Portable Strength Training", 44.99),
            ("SummitGear", "Ab Roller Wheel Knee Pad Core Workout Equipment Home Gym", 24.99),
        ],
        "Sportswear": [
            ("FitLife", "Performance Running Jacket Windproof Lightweight Reflective", 89.99),
            ("SportMax", "Compression Leggings High Performance Moisture Wicking Black", 54.99),
            ("ActiveGear", "Training Tank Top Racerback Breathable Quick Dry Workout", 29.99),
            ("EndurancePro", "Cycling Jersey Pro Fit Short Sleeve Moisture Wicking Men", 69.99),
            ("PeakPerformance", "Basketball Shorts Mesh Breathable Elastic Waist 7-Inch", 34.99),
            ("IronWill", "Track Suit 2-Piece Full Zip Hoodie Jogger Set Athletic", 89.99),
            ("TrailBlazer", "Thermal Base Layer Crew Neck Long Sleeve Winter Sports", 44.99),
            ("SummitGear", "Rain Jacket Waterproof Breathable Packable Outdoor Shell", 129.99),
        ],
        "Yoga": [
            ("FitLife", "Yoga Block Set 2-Piece Cork Eco Friendly Non-Slip", 24.99),
            ("SportMax", "Yoga Strap Cotton 8ft with D-Ring Loop Stretching Belt", 14.99),
            ("ActiveGear", "Yoga Bolster Pillow Rectangular Cotton Cover Meditation", 44.99),
            ("EndurancePro", "Yoga Wheel Backbend Stretching Helper Pilates Balance", 34.99),
            ("PeakPerformance", "Meditation Cushion Floor Pillow Round Yoga Mat Seat Zen", 39.99),
            ("IronWill", "Knee Pad Cushion Set 2-Pack Gardening Yoga Floor Padding", 19.99),
            ("TrailBlazer", "Yoga Towel Non-Slip Microfiber Hot Yoga Mat Cover", 22.99),
            ("SummitGear", "Balance Board Wobble Board Core Stability Trainer Wood", 59.99),
        ],
        "Cycling": [
            ("FitLife", "Mountain Bike 29-Inch 21-Speed Front Suspension Disc Brake", 499.99),
            ("SportMax", "Road Bike 700c 14-Speed Lightweight Aluminum Frame Racing", 699.99),
            ("ActiveGear", "Bike Helmet Adult Adjustable MIPS Safety Lightweight Ventilated", 89.99),
            ("EndurancePro", "Cycling Gloves Padded Gel Full Finger Carbon Knuckle Protection", 34.99),
            ("PeakPerformance", "Bike Lock Heavy Duty U-Lock Anti-Theft Secure Folding", 39.99),
            ("IronWill", "Bicycle Repair Kit Multi-Tool Tire Pump Patch Set Portable", 29.99),
            ("TrailBlazer", "Bike Lights Set LED Front Rear Rechargeable Waterproof", 24.99),
            ("SummitGear", "Electric Bike 500W 48V 20mph Foldable Commuter E-Bike", 1299.99),
        ],
        "Camping Gear": [
            ("FitLife", "Tent 4-Person Waterproof Dome Camping Shelter Easy Setup", 179.99),
            ("SportMax", "Sleeping Bag 3-Season 35F Envelope Mummy Adult Warm Outdoor", 69.99),
            ("ActiveGear", "Camping Stove Portable 2-Burner Propane Cooking Outdoor", 59.99),
            ("EndurancePro", "Hiking Backpack 65L Internal Frame Waterproof Daypack", 129.99),
            ("PeakPerformance", "Cooler 45-Quart Rotomolded Ice Chest Bear Proof Lockable", 249.99),
            ("IronWill", "Camping Chair Portable Quad Fold Outdoor Padded Armrest", 49.99),
            ("TrailBlazer", "Lantern LED Camping Light 1000 Lumens Rechargeable Collapsible", 34.99),
            ("SummitGear", "Survival Kit 22-in-1 Emergency Multi-Tool Fire Starter Gear", 39.99),
        ],
        "Water Bottles": [
            ("FitLife", "Stainless Steel Water Bottle 32oz Vacuum Insulated Double Wall", 29.99),
            ("SportMax", "Gym Water Bottle Shaker 28oz Leak Proof Protein Mixer", 14.99),
            ("ActiveGear", "Glass Water Bottle 20oz Silicone Sleeve BPA Free Pure", 19.99),
            ("EndurancePro", "Hydration Pack 2L Bladder Backpack Hands Free Running Hiking", 44.99),
            ("PeakPerformance", "Collapsible Water Bottle 22oz Flexible BPA Free Outdoor Camping", 12.99),
            ("IronWill", "Kids Water Bottle 14oz Spill Proof Straw Top Fun Design", 11.99),
            ("TrailBlazer", "Insulated Water Bottle 64oz Half Gallon Jug Cold 24hr", 34.99),
            ("SummitGear", "Aluminum Bottle 25oz Sports Squeeze Cap Lightweight Reusable", 16.99),
        ],
        "Gym Bags": [
            ("FitLife", "Duffel Bag 50L Large Sports Gym Bag Travel Weekender", 59.99),
            ("SportMax", "Backpack Gym Bag 40L Water Resistant Laptop Compartment", 49.99),
            ("ActiveGear", "Drawstring Backpack Cinch Sack 18L Lightweight Gym Gym", 14.99),
            ("EndurancePro", "Wet Dry Gym Bag 25L Waterproof Compartment Swimming", 39.99),
            ("PeakPerformance", "Travel Gym Bag 60L Rolling Duffle Suitcase Wheels Luggage", 89.99),
            ("IronWill", "Yoga Mat Bag 36-Inch Carry Strap with Pocket Mat Holder", 24.99),
            ("TrailBlazer", "Fanny Pack Running Belt 3-Pocket Waist Pack Phone Holder", 18.99),
            ("SummitGear", "Lunch Box Gym Cooler 20-Can Insulated Soft Sided Portable", 34.99),
        ],
    },
    "Beauty & Personal Care": {
        "Skincare": [
            ("GlowUp", "Vitamin C Serum Anti-Aging Hyaluronic Acid Brightening 1oz", 29.99),
            ("PureBeauty", "Moisturizer Face Cream SPF 30 Daily Hydrating Non-Greasy", 24.99),
            ("RadianceCo", "Retinol Eye Cream Anti Aging Dark Circles Fine Lines", 34.99),
            ("NaturalGlow", "Niacinamide Face Serum 10% Zinc 2% Oil Control Pore Minimizer", 22.99),
            ("LuxeLook", "Face Wash Cleanser Gentle Foaming Daily Hydrating 6oz", 19.99),
            ("FreshFace", "Sheet Mask Set 10-Pack Hydrogel Collagen Moisturizing Variety", 18.99),
            ("BloomCare", "Toner Facial Mist Rose Water Alcohol Free Balancing", 16.99),
            ("EssenceLab", "Exfoliating Scrub Face Body Microbeads Dead Skin Remover", 14.99),
        ],
        "Makeup": [
            ("GlowUp", "Foundation Liquid Full Coverage 24hr Wear Matte Finish 30ml", 39.99),
            ("PureBeauty", "Lipstick Set Long Lasting Creamy Matte 6-Pack Nude Collection", 29.99),
            ("RadianceCo", "Eyeshadow Palette 35-Color Neutral Matte Shimmer Professional", 44.99),
            ("NaturalGlow", "Mascara Volumizing Lengthening Waterproof Black Intense", 24.99),
            ("LuxeLook", "Concealer Full Coverage Creamy Liquid Brighten Under Eye 5ml", 22.99),
            ("FreshFace", "Makeup Brush Set 12-Piece Premium Synthetic Kabuki Foundation", 34.99),
            ("BloomCare", "Blush Palette 3-Color Powder Silky Finish Natural Glow", 19.99),
            ("EssenceLab", "Eyeliner Pencil Waterproof Long Wear Black Brown 2-Pack", 14.99),
        ],
        "Haircare": [
            ("GlowUp", "Shampoo Sulfate Free Biotin Volumizing Keratin 16oz", 22.99),
            ("PureBeauty", "Conditioner Moisturizing Argan Oil Smooth Silky 16oz", 22.99),
            ("RadianceCo", "Hair Mask Deep Conditioning Treatment Coconut Oil 8oz", 29.99),
            ("NaturalGlow", "Hair Serum Argan Oil Heat Protectant Shine Anti Frizz 4oz", 19.99),
            ("LuxeLook", "Hair Dryer Ionic Professional 1875W Diffuser Concentrator", 59.99),
            ("FreshFace", "Hair Brush Detangling Paddle Ventilated Smoothing Cushion", 16.99),
            ("BloomCare", "Dry Shampoo Volumizing Invisible Spray Refresh No Wash 5oz", 14.99),
            ("EssenceLab", "Hair Color Permanent Cream 6-Pack Dark Brown Ammonia Free", 12.99),
        ],
        "Fragrance": [
            ("GlowUp", "Eau de Parfum Floral Jasmine Rose Vanilla Long Lasting 3.4oz", 89.99),
            ("PureBeauty", "Cologne Citrus Sandalwood Musk Classic Scent 3.4oz Spray", 74.99),
            ("RadianceCo", "Perfume Roller Ball Set 5-Pack Travel Size Variety Fragrance", 34.99),
            ("NaturalGlow", "Body Mist Refreshing Ocean Breeze Light Scent 8oz Spray", 19.99),
            ("LuxeLook", "Designer Perfume Gift Set EDP 3.4oz Body Lotion Shower Gel", 129.99),
            ("FreshFace", "Room Spray Linen Fresh Scent Home Fragrance 4oz 2-Pack", 24.99),
            ("BloomCare", "Essential Oil Blend Lavender Chamomile Aromatherapy 10ml", 16.99),
            ("EssenceLab", "Solid Perfume Tin Pocket Size Natural Scent Balm 0.5oz", 14.99),
        ],
        "Bath & Body": [
            ("GlowUp", "Body Lotion Shea Butter Cocoa Cream Deep Moisture 16oz", 18.99),
            ("PureBeauty", "Body Wash Hydrating Coconut Milk Shower Gel 20oz Pump", 16.99),
            ("RadianceCo", "Shower Steamer Set Aromatherapy 6-Pack Eucalyptus Mint", 14.99),
            ("NaturalGlow", "Soap Bar Handmade Goat Milk Oatmeal Natural Organic 4-Pack", 22.99),
            ("LuxeLook", "Bath Bomb Gift Set 12-Pack Fizzy Essential Oil Scented", 29.99),
            ("FreshFace", "Hand Sanitizer Gel 62% Alcohol Moisturizing 12-Pack 2oz", 19.99),
            ("BloomCare", "Sugar Body Scrub Coconut Coffee Exfoliating 12oz Jar", 24.99),
            ("EssenceLab", "Deodorant Natural Aluminum Free Long Lasting Coconut 2.6oz", 12.99),
        ],
        "Grooming": [
            ("GlowUp", "Beard Trimmer Cordless Rechargeable Waterproof Adjustable Length", 44.99),
            ("PureBeauty", "Electric Razor Foil Shaver Wet Dry Pop-Up Trimmer Cordless", 69.99),
            ("RadianceCo", "Nail Clipper Set Stainless Steel 10-Piece Manicure Pedicure Kit", 18.99),
            ("NaturalGlow", "Waxing Kit Hard Wax Beans Microwave 16oz Hair Removal Sensitive", 29.99),
            ("LuxeLook", "Tweezers Precision Tip Stainless Steel Slanted Professional", 14.99),
            ("FreshFace", "Lip Balm SPF 15 Moisturizing Vitamin E 6-Pack Assorted Flavor", 11.99),
            ("BloomCare", "Face Roller Jade Gua Sha Set Lymphatic Drainage Natural Stone", 19.99),
            ("EssenceLab", "Towel Set Microfiber Hair Towel 2-Pack Quick Dry Absorbent", 16.99),
        ],
        "Sunscreen": [
            ("GlowUp", "Sunscreen SPF 50 Mineral Zinc Oxide Face Non-White Cast", 24.99),
            ("PureBeauty", "SPF 30 Sunscreen Spray Water Resistant Sport Broad Spectrum 6oz", 17.99),
            ("RadianceCo", "After Sun Aloe Vera Gel Cooling Soothing Sunburn Relief 12oz", 14.99),
            ("NaturalGlow", "Tinted Sunscreen SPF 40 Mineral Sunblock Sheer Matte Finish", 29.99),
            ("LuxeLook", "Kids Sunscreen Stick SPF 50 Water Resistant Hypoallergenic 1.5oz", 15.99),
            ("FreshFace", "Sun Protection Lip Balm SPF 50 Moisturizing Coconut 3-Pack", 12.99),
            ("BloomCare", "UV Umbrella Compact Travel Folding Black Coating UPF 50+", 24.99),
            ("EssenceLab", "Sun Hat Wide Brim UPF 50+ Beach Safari Bucket Hat Packable", 19.99),
        ],
    },
    "Toys & Games": {
        "Board Games": [
            ("FunFactory", "Catan Settlers Strategy Board Game Family 3-4 Player Ages 10+", 44.99),
            ("PlayWorld", "Ticket to Ride Cross Country Train Adventure Board Game", 49.99),
            ("ToyChest", "Codenames Word Party Social Deduction Game Family 4-8 Player", 22.99),
            ("KidJoy", "Jenga Classic Wooden Stacking Tower Game Family 2+ Player", 24.99),
            ("ImagiNation", "Chess Set Wooden Magnetic Travel Board Game 12-Inch", 34.99),
            ("HappyPlay", "Scrabble Original Crossword Word Game Family Board 2-4 Player", 29.99),
            ("GameOn", "Monopoly Classic Edition Property Trading Board Game Family", 34.99),
            ("BuildMaster", "Checkers Backgammon 2-in-1 Set Wooden Board Classic Games", 27.99),
        ],
        "Puzzles": [
            ("FunFactory", "Jigsaw Puzzle 1000 Piece Adult Landscape Scenic Mountain Lake", 19.99),
            ("PlayWorld", "3D Puzzle Wooden Model Architecture Notre Dame Cathedral Kit", 34.99),
            ("ToyChest", "Floor Puzzle Kids 48-Piece Extra Large Dinosaur World Science", 16.99),
            ("KidJoy", "Rubic's Cube Speed Puzzle 3x3x3 Classic Brain Teaser Toy", 12.99),
            ("ImagiNation", "Sudoku Puzzle Book 1000 Puzzles Easy Medium Hard Brain Game", 9.99),
            ("HappyPlay", "Metal Wire Puzzle Set 10-Pack Brain Teaser IQ Mind Bender", 14.99),
            ("GameOn", "Laser Maze Logic Puzzle Game STEM Toy Light Reflection Challenge", 29.99),
            ("BuildMaster", "Crossword Puzzle Book Large Print 200 Puzzles Variety Challenge", 11.99),
        ],
        "Action Figures": [
            ("FunFactory", "Superhero Action Figure 12-Inch Poseable Body with Accessories", 24.99),
            ("PlayWorld", "Space Ranger Commander Figure 6-Inch Premium Articulated", 19.99),
            ("ToyChest", "Dinosaur Figure Set 10-Pack Realistic T-Rex Triceratops Velociraptor", 29.99),
            ("KidJoy", "Robot Action Figure Transforming LED Light Sound Mech Warrior", 34.99),
            ("ImagiNation", "Fantasy Warrior Elf Knight Figure 8-Inch Scale Weapon Set", 22.99),
            ("HappyPlay", "Animal Figure Set Wild Safari 15-Pack Plastic Zoo Animals", 17.99),
            ("GameOn", "Ninja Warrior Action Figure 6-Inch Battle Gear Moveable Joints", 19.99),
            ("BuildMaster", "Marvel Legends Series Spider-Man 6-Inch Action Figure Collectible", 29.99),
        ],
        "Building Sets": [
            ("FunFactory", "Building Blocks 1000-Piece Classic Construction Set Creative Kids", 39.99),
            ("PlayWorld", "Magnetic Tiles 100-Piece 3D Building Blocks STEM Magnetic Set", 49.99),
            ("ToyChest", "Lego City Police Station 60246 Building Kit 745 Pieces", 89.99),
            ("KidJoy", "Wooden Block Set 60-Piece Natural Hardwood Building Blocks Toddler", 29.99),
            ("ImagiNation", "Marble Run 150-Piece Roller Coaster Construction Building Track", 34.99),
            ("HappyPlay", "Gear Building Set 75-Piece Interlocking Gears Wheels STEM Toy", 27.99),
            ("GameOn", "Architecture Model Kit Famous Landmarks Eiffel Tower 3D Puzzle", 44.99),
            ("BuildMaster", "Bridge Building Kit 200-Piece Truss Structure Engineering STEM", 54.99),
        ],
        "Educational Toys": [
            ("FunFactory", "Science Kit 50+ Experiments Chemistry Physics Lab STEM Learning", 34.99),
            ("PlayWorld", "Microscope Kids 40x-1000x LED Zoom Beginner Scientist Kit", 49.99),
            ("ToyChest", "Telescope Astronomy 70mm Refractor Tripod Moon Star Gazing", 79.99),
            ("KidJoy", "Robot Building Kit Solar Powered 3-in-1 STEM Coding Toy", 29.99),
            ("ImagiNation", "Math Game Multiplication Table Learning Toy Counting Beads", 24.99),
            ("HappyPlay", "Alphabet Flash Cards ABC Learning Letter Recognition 52 Cards", 14.99),
            ("GameOn", "Circuit Board Kit Snap Circuits Electronics 100+ Projects STEM", 54.99),
            ("BuildMaster", "Globe 10-Inch Educational World Earth Map Light Up Geography", 39.99),
        ],
        "Outdoor Play": [
            ("FunFactory", "Kite Large Delta Wing Easy Flyer 5ft Rainbow Outdoor Toy", 19.99),
            ("PlayWorld", "Scooter Kick Kids 2-Wheel Adjustable Height Folding Lean Steer", 69.99),
            ("ToyChest", "Bubble Machine Automatic 5000+ Bubbles Minute LED Light Outdoor", 24.99),
            ("KidJoy", "Water Gun Super Soaker 50oz Blaster High Pressure Squirt Toy", 29.99),
            ("ImagiNation", "Trampoline 8-Foot Outdoor Rebounder Enclosure Safety Net Kids", 249.99),
            ("HappyPlay", "Playhouse Kids Outdoor Wooden Climbing Fort Swing Set", 399.99),
            ("GameOn", "Slip and Slide Water Slide 20ft Inflatable Backyard Summer Toy", 44.99),
            ("BuildMaster", "Sandbox Sand Play Set 8-Piece Bucket Shovel Rake Molds Toys", 29.99),
        ],
        "Video Games": [
            ("FunFactory", "Soulsborne Reckoning RPG PlayStation 5 Standard Edition Disc", 69.99),
            ("PlayWorld", "Racing Circuit Pro Xbox Series X Racing Simulation Disc", 59.99),
            ("ToyChest", "Ninja Clash Royale Battle Royale Multiplayer Nintendo Switch", 49.99),
            ("KidJoy", "Puzzle Adventure Quest Family Friendly Puzzle Platformer Switch", 39.99),
            ("ImagiNation", "Survival Evolved Island Open World Crafting PS5 PlayStation 5", 54.99),
            ("HappyPlay", "Sports Championship 2024 Basketball Football Soccer Multi-Sport", 59.99),
            ("GameOn", "Stealth Operative Tactical Shooter PC DVD-ROM Windows 10/11", 44.99),
            ("BuildMaster", "Educational Explorer Nature Discovery Simulation Kids PC", 29.99),
        ],
    },
    "Grocery & Gourmet": {
        "Snacks": [
            ("FreshFarm", "Mixed Nuts Roasted Salted 2lb Bulk Premium Almonds Cashews Pecans", 19.99),
            ("NatureBest", "Potato Chips Sea Salt 8oz Bag Kettle Cooked Crunchy Snack 6-Pack", 24.99),
            ("DailyGoods", "Dark Chocolate Almond Butter Bar 3.5oz Organic 70% Cacao", 5.99),
            ("PureHarvest", "Beef Jerky Original 8oz High Protein 100% Grass Fed Bites", 14.99),
            ("GreenChoice", "Trail Mix Energy Blend 2lb Dried Fruit Nuts Seeds Healthy Snack", 18.99),
            ("SmartShop", "Protein Bars 12-Pack Chocolate Peanut Butter 20g Protein Each", 27.99),
            ("TasteTrail", "Popcorn Microwave 100-Calorie Single Serve Butter Flavor 30-Pack", 19.99),
            ("OrganicValley", "Crackers Organic Whole Wheat Sea Salt 9oz Box 6-Pack", 22.99),
        ],
        "Beverages": [
            ("FreshFarm", "Orange Juice Fresh Pressed 64oz 100% Pure No Pulp Refrigerated", 6.99),
            ("NatureBest", "Green Tea Matcha Powder Ceremonial Grade 4oz Japanese Stone Ground", 29.99),
            ("DailyGoods", "Sparkling Water 12-Pack 12oz Cans Lime Flavored Zero Sugar", 7.99),
            ("PureHarvest", "Coconut Water 100% Pure 33.8oz 4-Pack Hydration Electrolytes", 14.99),
            ("GreenChoice", "Protein Shake Chocolate 14oz 30g Protein Ready to Drink 6-Pack", 24.99),
            ("SmartShop", "Energy Drink Zero Sugar 16oz Can Variety Pack Electrolytes 12-Pack", 21.99),
            ("TasteTrail", "Kombucha Gingerberry Probiotic 16oz 4-Pack Live Fermented Tea", 12.99),
            ("OrganicValley", "Apple Juice Organic 64oz 100% Juice No Sugar Added Glass Bottle", 8.99),
        ],
        "Pantry Staples": [
            ("FreshFarm", "Organic Brown Rice 5lb Bag Long Grain Wholesome Whole Grain", 11.99),
            ("NatureBest", "Pasta Spaghetti 16oz Box 100% Semolina Italian Style 12-Pack", 21.99),
            ("DailyGoods", "Olive Oil Extra Virgin 25.5oz First Cold Pressed Glass Bottle", 24.99),
            ("PureHarvest", "Peanut Butter Creamy 40oz Jar No Stir No Sugar Added Natural", 12.99),
            ("GreenChoice", "Black Beans Canned 15oz Organic Low Sodium 12-Pack", 18.99),
            ("SmartShop", "Flour All Purpose 5lb Bag Unbleached Enriched Wheat Pre-Sifted", 7.99),
            ("TasteTrail", "Honey Pure Wildflower 12oz Squeeze Bottle Raw Unfiltered", 14.99),
            ("OrganicValley", "Canned Tomatoes Crushed 28oz Organic Italian Style 6-Pack", 16.99),
        ],
        "Organic Foods": [
            ("FreshFarm", "Organic Quinoa 2lb Bag White Whole Grain Gluten Free Protein Rich", 14.99),
            ("NatureBest", "Organic Almonds Raw 2lb Unsalted Bulk Natural Vitamin E Source", 21.99),
            ("DailyGoods", "Organic Maple Syrup 100% Pure Grade A 12oz Glass Bottle Vermont", 19.99),
            ("PureHarvest", "Organic Coconut Oil Extra Virgin 16oz Cold Pressed Unrefined", 16.99),
            ("GreenChoice", "Organic Chicken Bone Broth 32oz 6-Pack Grass Fed High Protein", 27.99),
            ("SmartShop", "Organic Chia Seeds 2lb Raw Superfood Omega 3 Fiber Gluten Free", 18.99),
            ("TasteTrail", "Organic Granola Maple Pecan 12oz Crunchy Oat Cluster Cereal", 9.99),
            ("OrganicValley", "Organic Turmeric Powder 8oz Premium Ground Curcumin Spice", 12.99),
        ],
        "Coffee & Tea": [
            ("FreshFarm", "Coffee Beans Medium Roast 12oz Arabica Single Origin Colombia", 19.99),
            ("NatureBest", "Espresso Roast Ground Coffee Dark Roast Fine Grind 16oz Bag", 16.99),
            ("DailyGoods", "Coffee Capsules Variety Pack 60-Pack Arabica Pods Nespresso Compatible", 39.99),
            ("PureHarvest", "Matcha Latte Mix 8oz Instant Japanese Green Tea Powder Creamy", 24.99),
            ("GreenChoice", "Herbal Tea Sampler 36-Bags Chamomile Peppermint Lavender Caffeine Free", 14.99),
            ("SmartShop", "Cold Brew Coffee Concentrate 32oz Caramel Flavored Ready to Drink", 11.99),
            ("TasteTrail", "Loose Leaf Tea Assortment 6-Tin Premium Darjeeling Earl Grey Green", 29.99),
            ("OrganicValley", "Decaf Coffee Ground Swiss Water Process 12oz Organic Chemical Free", 18.99),
        ],
        "Chocolates": [
            ("FreshFarm", "Milk Chocolate Bar 3.5oz Creamy Belgium Chocolate Smooth Classic", 4.99),
            ("NatureBest", "Dark Chocolate 72% Cacao 3.5oz Belgian Single Origin Bittersweet", 5.99),
            ("DailyGoods", "Chocolate Truffle Box 24-Piece Assorted Dark Milk White Ganache", 34.99),
            ("PureHarvest", "White Chocolate Bar 3oz Creamy Vanilla Cocoa Butter Smooth", 4.99),
            ("GreenChoice", "Organic Chocolate Almonds 12oz Dark Chocolate Covered Roasted", 14.99),
            ("SmartShop", "Hot Cocoa Mix 28oz Canister Rich Chocolate 30 Servings Marshmallows", 12.99),
            ("TasteTrail", "Chocolate Gift Basket Assorted 1.5lb Truffles Caramels Nougat", 44.99),
            ("OrganicValley", "Cacao Nibs 8oz Organic Raw Crushed Cocoa Beans Superfood", 11.99),
        ],
        "International Foods": [
            ("FreshFarm", "Soy Sauce 40oz Kikkoman Traditional Japanese Brewed Seasoning", 8.99),
            ("NatureBest", "Pasta Sauce Marinara 24oz Italian Style 100% Natural Jar 6-Pack", 29.99),
            ("DailyGoods", "Basmati Rice 5lb Premium Long Grain Aromatic Indian Rice", 16.99),
            ("PureHarvest", "Coconut Milk 13.5oz Unsweetened Natural Thai Kitchen 12-Pack", 24.99),
            ("GreenChoice", "Tortilla Chips 12oz Restaurant Style White Corn 6-Pack", 22.99),
            ("SmartShop", "Salsa Verde 16oz Medium Roasted Tomatillo Cilantro Lime 2-Pack", 14.99),
            ("TasteTrail", "Sriracha Hot Sauce 17oz Rooster Sauce Spicy Chili Garlic 2-Pack", 16.99),
            ("OrganicValley", "Ghee Clarified Butter 16oz Organic Grass Fed A2 Cooking Oil", 19.99),
        ],
    },
    "Automotive": {
        "Car Accessories": [
            ("AutoPro", "Floor Mats Custom Fit All Weather Heavy Duty Car Truck Black", 59.99),
            ("DriveGear", "Seat Cover Full Set Universal Fit Neoprene Waterproof Red", 89.99),
            ("CarCare", "Steering Wheel Cover Genuine Leather 15-Inch Black Stitch", 24.99),
            ("RoadMaster", "Phone Mount Car Dashboard Holder Universal GPS Windshield", 19.99),
            ("TurboFit", "Sunshade Windshield Reflector 60x30 Premium Dual Layer", 22.99),
            ("ShieldAuto", "Trunk Organizer Collapsible Heavy Duty Storage Bag 50L", 34.99),
            ("MotoZone", "LED Interior Lights Kit RGB 4-Pack App Control Footwell", 29.99),
            ("GearHead", "Cargo Liner SUV Truck 100% Waterproof Back Seat Protector", 44.99),
        ],
        "Car Electronics": [
            ("AutoPro", "Dash Cam 4K Front and Rear Dual 170 Wide Angle WiFi GPS", 149.99),
            ("DriveGear", "Car Radio Stereo Android Auto Apple CarPlay 7-Inch Touchscreen", 129.99),
            ("CarCare", "GPS Navigator 7-Inch Touch Screen Free Lifetime Maps Truck", 199.99),
            ("RoadMaster", "Bluetooth FM Transmitter Wireless Handsfree Car Kit 30W QC", 34.99),
            ("TurboFit", "Backup Camera Wireless License Plate Night Vision HD 1080p", 69.99),
            ("ShieldAuto", "Parking Sensor Kit 4-Sensor LCD Display Rear Bumper Alarm", 44.99),
            ("MotoZone", "OBD2 Scanner Bluetooth Wifi Diagnostic Tool Check Engine Car", 39.99),
            ("GearHead", "Car Jump Starter 3000A Battery Pack 12V Portable Power Bank USB", 89.99),
        ],
        "Cleaning & Detailing": [
            ("AutoPro", "Car Wash Soap 64oz PH Balanced High Foam Shampoo Concentrate", 19.99),
            ("DriveGear", "Microfiber Towel Set 12-Pack 16x16 Premium Dual Pile Detailing", 24.99),
            ("CarCare", "Pressure Washer Electric 2000PSI 1.3GPM Portable Car Cleaning", 159.99),
            ("RoadMaster", "Wax Car Carnauba Paste Premium Shine Protection 16oz", 29.99),
            ("TurboFit", "Interior Cleaner 32oz All Purpose Non-Toxic UV Protection Spray", 14.99),
            ("ShieldAuto", "Glass Cleaner Streak Free 24oz Ammonia Free Formula 3-Pack", 17.99),
            ("MotoZone", "Wheel Cleaner 32oz Iron Remover Brake Dust Acid Free Spray", 22.99),
            ("GearHead", "Ceramic Coating Kit 9H Hardness 50cc Professional Nano Polish", 69.99),
        ],
        "Oils & Fluids": [
            ("AutoPro", "Motor Oil Full Synthetic 5W-30 5-Quart Bottle API SN Plus", 34.99),
            ("DriveGear", "Transmission Fluid Automatic 1-Gallon DEXRON VI Compatible", 29.99),
            ("CarCare", "Coolant Antifreeze 50/50 Pre-Mixed 1-Gallon All Makes Models", 19.99),
            ("RoadMaster", "Brake Fluid DOT 4 32oz Synthetic High Boiling Point 550F", 16.99),
            ("TurboFit", "Windshield Washer Fluid 1-Gallon Bug Remover De-Icer Rain Repel", 7.99),
            ("ShieldAuto", "Power Steering Fluid 32oz Universal Complete Compatibility", 14.99),
            ("MotoZone", "Fuel Injector Cleaner 12oz 2-Pack Fuel System Treatment Additive", 12.99),
            ("GearHead", "Diesel Exhaust Fluid DEF 2.5 Gallon S shelf Stable Urea Solution", 19.99),
        ],
        "Interior Accessories": [
            ("AutoPro", "Car Seat Organizer Back Seat Storage 2-Pack Tablet Pocket", 21.99),
            ("DriveGear", "Air Freshener Vent Clip 6-Pack Long Lasting Ocean Scent New Car", 12.99),
            ("CarCare", "Car Mat Rubber Heavy Duty Floor Liner Custom Fit Front Rear", 69.99),
            ("RoadMaster", "Pet Barrier SUV Cargo Divider Adjustable Dog Net Mesh Screen", 39.99),
            ("TurboFit", "Cup Holder Expander Car Insert 2-in-1 Adjustable Cup Expander", 14.99),
            ("ShieldAuto", "Sunglasses Holder Clip On Sun Visor Organizer Carbon Fiber", 9.99),
            ("MotoZone", "Car Trash Can Small Garbage Bin Waterproof Leakproof 1.5 Gallon", 17.99),
            ("GearHead", "Memory Foam Car Seat Cushion Back Lumbar Support Driver Comfort", 34.99),
        ],
        "Exterior Accessories": [
            ("AutoPro", "Car Cover All Weather Waterproof 5-Layer UV Protection Vehicle", 89.99),
            ("DriveGear", "Mud Flaps Splash Guards Front Rear Set Universal Black", 29.99),
            ("CarCare", "Hood Bug Deflector Smoke Shield Front Chrome Look Truck SUV", 49.99),
            ("RoadMaster", "License Plate Frame Black Carbon Fiber Look 2-Pack Screws", 14.99),
            ("TurboFit", "LED Light Bar 52-Inch 300W Off Road Light Bar Flood Beam Combo", 99.99),
            ("ShieldAuto", "Side Step Running Board Nerf Bar 3-Inch Oval Aluminum Black", 199.99),
            ("MotoZone", "Bike Rack Trunk Mount 2-Bike Capacity Folding Heavy Duty", 119.99),
            ("GearHead", "Roof Rack Cargo Basket 53x37x6 Universal Steel Mesh Crossbars", 169.99),
        ],
        "Car Care Kits": [
            ("AutoPro", "Emergency Roadside Kit 24-Piece Jumper Cables Reflective Triangle", 39.99),
            ("DriveGear", "First Aid Kit Car 150-Piece Emergency Medical Supplies Bag", 29.99),
            ("CarCare", "Tire Inflator Portable Air Pump Digital 12V Auto Shutoff 150PSI", 49.99),
            ("RoadMaster", "Car Charger 12V 3 USB Ports 4.8A Fast Charging Adapter", 14.99),
            ("TurboFit", "Snow Chain Tire Cable Emergency Traction Pair Universal Size", 99.99),
            ("ShieldAuto", "Car Escape Tool Seatbelt Cutter Window Breaker Hammer Emergency 4-in-1", 16.99),
            ("MotoZone", "Portable Air Compressor 12V 2000mA 150PSI Heavy Duty Tire Pump", 34.99),
            ("GearHead", "Detailing Cart 3-Tier Portable Utility Rolling Tool Box Organizer", 89.99),
        ],
    },
    "Pet Supplies": {
        "Dog Food": [
            ("PetJoy", "Dry Dog Food Chicken Rice 30lb Bag Adult All Breed Complete", 44.99),
            ("HappyPaws", "Wet Dog Food 13oz Can Beef Stew Chunks 12-Pack Grain Free", 29.99),
            ("FurryFriends", "Puppy Food Small Breed Chicken 15lb Bag Complete Nutrition", 34.99),
            ("PetCare", "Freeze Dried Dog Food Raw 1lb Chicken Liver Topper Grain Free", 24.99),
            ("AnimalLodge", "Dog Treats Training Bites 16oz Soft Chewy Chicken 3-Pack", 19.99),
            ("PurrfectPet", "Large Breed Dog Food Salmon Sweet Potato 30lb Adult Giant", 54.99),
            ("WildTails", "Dental Chews Fresh Breath Clean Teeth 36-Count Mint Flavor", 16.99),
            ("PetNest", "Senior Dog Food Joint Support Glucosamine 15lb Small Kibble", 39.99),
        ],
        "Cat Food": [
            ("PetJoy", "Dry Cat Food Salmon 7lb Bag Adult Indoor Hairball Control", 22.99),
            ("HappyPaws", "Wet Cat Food 3oz Poultry Variety Pack 24-Count Pate Minced", 32.99),
            ("FurryFriends", "Kitten Food Chicken 3lb Bag Complete Starter Formula Wet 12-Pack", 28.99),
            ("PetCare", "Grain Free Cat Food Tuna Recipe 7lb Dry Limited Ingredient", 26.99),
            ("AnimalLodge", "Cat Treats Crunchy Salmon 2oz 3-Pack Soft Center Hairball", 12.99),
            ("PurrfectPet", "Senior Cat Food Urinary Health 7lb Chicken Meal Formula", 24.99),
            ("WildTails", "Catnip Organic Loose Dried 4oz Premium Catnip Toy Refill", 11.99),
            ("PetNest", "Liquid Cat Supplement 8oz Salmon Oil Omega 3 Skin Coat", 19.99),
        ],
        "Pet Toys": [
            ("PetJoy", "Dog Chew Toy Indestructible TPR Bone Tough Durable Large Puppy", 16.99),
            ("HappyPaws", "Cat Wand Toy Feather String Teaser Interactive 3-Pack Assorted", 11.99),
            ("FurryFriends", "Fetch Ball Tennis Dog 6-Pack Non-Toxic Squeaky Rubber Latex", 14.99),
            ("PetCare", "Plush Squeaky Toy Dog 8-Inch Bear with Squeaker Machine Washable", 12.99),
            ("AnimalLodge", "Cat Toy Mouse Set 10-Pack Crinkle Fabric Realistic Fur Catnip", 15.99),
            ("PurrfectPet", "Rope Tug Toy Dog 24-Inch Cotton Knotted Heavy Duty Chew", 11.99),
            ("WildTails", "Interactive Treat Puzzle Dog Enrichment Brain Game Feeder", 22.99),
            ("PetNest", "Laser Pointer Cat Toy USB Rechargeable Light Exercise Play", 14.99),
        ],
        "Pet Beds": [
            ("PetJoy", "Dog Bed Orthopedic Memory Foam 36x24 Waterproof Liner Cover", 59.99),
            ("HappyPaws", "Cat Bed Cave Plush Donut Shape Washable Small Pet Warm Cozy", 34.99),
            ("FurryFriends", "Elevated Dog Cot Outdoor Mesh Platform Bed 42x32 Anti Flea", 49.99),
            ("PetCare", "Pet Sofa Bed Medium Tufted Cushion Bordeaux Velvet Luxury", 79.99),
            ("AnimalLodge", "Heated Dog Bed 25W Self Warming Indoor Thermostat Pad Small", 44.99),
            ("PurrfectPet", "Travel Pet Bed Folding Soft Portable Puppy Mat Car Crate Liner", 29.99),
            ("WildTails", "Waterproof Dog Bed Outdoor Deck Patio Quick Dry Foam Filled", 55.99),
            ("PetNest", "Bolster Dog Bed Raised Rim Anti Anxiety Calming Donut Round", 64.99),
        ],
        "Pet Grooming": [
            ("PetJoy", "Pet Hair Clipper Grooming Kit Low Noise Cordless Rechargeable", 49.99),
            ("HappyPaws", "Dog Shampoo Oatmeal 16oz Soothing Itchy Skin Lavender Scent", 14.99),
            ("FurryFriends", "Nail Grinder Pet Electric Rechargeable Safe Guard Painless 2-Speed", 29.99),
            ("PetCare", "Grooming Glove Dog Cat Shedding Brush Deshedding Mitt Silicone", 14.99),
            ("AnimalLodge", "Cat Brush Self Cleaning Slicker Pin Comb Fine Wire Pet Hair", 12.99),
            ("PurrfectPet", "Pet Toothbrush Set 3-Pack Dental Kit Finger Brush Toothpaste", 16.99),
            ("WildTails", "Wipes Pet Deodorizing 100-Count Hypoallergenic Aloe Cucumber", 11.99),
            ("PetNest", "Flea Comb Dog Cat Fine Tooth Stainless Steel Small Medium Tight", 9.99),
        ],
        "Pet Accessories": [
            ("PetJoy", "Dog Collar Leather Adjustable Heavy Duty 1-Inch Brass Buckle", 24.99),
            ("HappyPaws", "Cat Harness Escape Proof Soft Mesh Vest with Leash Set Adjustable", 19.99),
            ("FurryFriends", "Leash Dog Rope 6-Feet Heavy Duty Reflective Nylon Strong Handle", 16.99),
            ("PetCare", "Pet Water Bottle Portable Drinking Dispenser 18oz Leak Proof Dog", 14.99),
            ("AnimalLodge", "Food Bowl Dog Stainless Steel Non Skid 4-Cup 2-Pack Raised", 22.99),
            ("PurrfectPet", "Pet ID Tag Custom Engraved Stainless Steel Bone Shape 2-Line", 12.99),
            ("WildTails", "Car Seat Cover Dog Hammock Waterproof Heavy Duty Scratch Proof", 39.99),
            ("PetNest", "Muzzle Dog Breathable Soft Mesh Adjustable Comfort Fit Training", 16.99),
        ],
    },
    "Office & Stationery": {
        "Desks & Chairs": [
            ("WorkSpace", "Standing Desk 60x30 Electric Height Adjustable Table with Drawer", 499.99),
            ("OfficePro", "Office Chair Ergonomic Mesh High Back Lumbar Support Adjustable", 299.99),
            ("StationeryKing", "Computer Desk 48-Inch Writing Table with Shelves Home Office", 179.99),
            ("DeskMate", "Conference Chair Mid Back Swivel Padded Seat Armrest Home Office", 199.99),
            ("PaperPlus", "L Shaped Desk 63-Inch Corner Computer Desk with Storage Shelves", 349.99),
            ("OrganizedLife", "Monitor Stand Riser Adjustable Height Bamboo Desk Organizer Shelf", 34.99),
            ("WriteWell", "Drafting Table Height Adjustable Slant Board Desk Architect", 249.99),
            ("ArtisanCraft", "Desk Mat Extra Large 36x17 Leather Waterproof Office Blotter", 44.99),
        ],
        "Notebooks & Pens": [
            ("WorkSpace", "Notebook Hard Cover 240-Page Dotted Grid A5 Classic Black", 19.99),
            ("OfficePro", "Ballpoint Pen Set 12-Pack 1.0mm Medium Point Blue Ink Retractable", 9.99),
            ("StationeryKing", "Gel Pen Set 20-Pack 0.7mm Bold Colorful Roller Assorted Ink", 14.99),
            ("DeskMate", "Spiral Notebook 8x10.5 200-Page College Ruled 5-Subject Pastel", 12.99),
            ("PaperPlus", "Fountain Pen Set 3-Pack Medium Nib Ink Cartridges Gift Box", 39.99),
            ("OrganizedLife", "Highlighters Chisel Tip 12-Pack Assorted Neon Colors Smear Safe", 11.99),
            ("WriteWell", "Composition Notebook Wide Ruled 100 Page Black Marble 3-Pack", 10.99),
            ("ArtisanCraft", "Bullet Journal 160GSM 248-Point Dotted Hardcover Vegan Leather", 28.99),
        ],
        "Printers & Supplies": [
            ("WorkSpace", "Laser Printer All-in-One Black White Wireless Duplex Print Copy Scan", 249.99),
            ("OfficePro", "Inkjet Printer Color Wireless Photo Printing Scanner Copier 3-in-1", 129.99),
            ("StationeryKing", "Label Maker Thermal Direct Print Bluetooth Organization Tapes", 49.99),
            ("DeskMate", "Toner Cartridge High Yield HP 26X Black 9200 Pages Compatible", 89.99),
            ("PaperPlus", "Printer Paper Bright White 5000 Sheets 8.5x11 20lb Case Multipurpose", 54.99),
            ("OrganizedLife", "Photo Paper Glossy 8.5x11 50-Sheet Pack Inkjet Printable 185gsm", 19.99),
            ("WriteWell", "Laminator 12-Inch Thermal Roll Pouch Laminating Machine Quick Warm Up", 39.99),
            ("ArtisanCraft", "Shredder Paper Micro Cut 12-Sheet Cross Cut Heavy Duty Security", 99.99),
        ],
        "Organization": [
            ("WorkSpace", "Desk Organizer Multi Compartment Drawer Pencil Pen Holder Mesh", 24.99),
            ("OfficePro", "File Cabinet 2-Drawer Vertical Lockable Letter Size Black Home Office", 89.99),
            ("StationeryKing", "Bookshelf 4-Tier Open Storage Shelf Unit Metal Frame Wood Board", 69.99),
            ("DeskMate", "Magazine Holder Wall Mount 3-Pack Clear Acrylic Letter File", 19.99),
            ("PaperPlus", "Cable Management Box Under Desk Wire Cover 5-Slot Cord Organizer", 29.99),
            ("OrganizedLife", "Paper Tray Stackable 3-Tier Desktop Letter A4 Organizer Mesh", 22.99),
            ("WriteWell", "Pen Cup Pencil Holder Large Capacity Desk Caddy Canvas 9-Compartment", 16.99),
            ("ArtisanCraft", "Name Plate Desk Engravable Acrylic 12-Inch 2-Line Custom Office Sign", 29.99),
        ],
        "School Supplies": [
            ("WorkSpace", "Backpack School Kids Laptop Compartment Padded Straps 18-Inch", 39.99),
            ("OfficePro", "Pencil Case Large Capacity 3-Layer Stand Up Pen Bag Canvas Case", 14.99),
            ("StationeryKing", "Scissors 8-Inch Titanium Coated Ultra Sharp Stainless Steel Office", 9.99),
            ("DeskMate", "Stapler 20-Sheet Capacity Classic Design Black Desk Stapler with Staples", 12.99),
            ("PaperPlus", "Tape Dispenser Desktop 2-Inch Core Heavy Duty Non-Slip Base", 16.99),
            ("OrganizedLife", "Binder 3-Ring 1-Inch Round Ring View Cover Clear 12-Pack", 24.99),
            ("WriteWell", "Calculator Scientific 417 Functions 16-Digit Solar Battery Dual Power", 22.99),
            ("ArtisanCraft", "Ruler 12-Inch Stainless Steel Metric Imperial Double Sided 4-Pack", 11.99),
        ],
        "Art Supplies": [
            ("WorkSpace", "Colored Pencils 72-Pack Premium Soft Core Vibrant Coloring Art Set", 34.99),
            ("OfficePro", "Watercolor Paint Set 36-Pan Artist Grade Colors Paint Brush Kit", 29.99),
            ("StationeryKing", "Acrylic Paint Set 24-Color 2oz Tubes Waterproof Art Supplies Canvas", 49.99),
            ("DeskMate", "Sketchbook 9x12 100-Sheet 60lb Drawing Paper Spiral Bound Pad", 16.99),
            ("PaperPlus", "Easel Adjustable Standing Floor Display Aluminum Tripod Artist 68-Inch", 59.99),
            ("OrganizedLife", "Oil Pastels 50-Pack Soft Chalk Drawing Artist Quality Assorted Color", 19.99),
            ("WriteWell", "Canvas 16x20 Stretched Triple Primed Cotton 4-Pack Professional Grade", 34.99),
            ("ArtisanCraft", "Clay Modeling Set 24-Blocks Sculpting Tools Polymer Oven Bake 30-Piece", 24.99),
        ],
    },
    "Baby & Kids": {
        "Diapers & Wipes": [
            ("BabyJoy", "Diapers Newborn Size 1 8-14lbs 50-Count Ultra Absorbent Dry", 24.99),
            ("LittleStars", "Baby Wipes 99% Water 720-Count Unscented 12-Pack Sensitive Skin", 32.99),
            ("TinyTot", "Diapers Size 4 22-37lbs 100-Count Leak Protection Wetness Indicator", 38.99),
            ("NurtureBaby", "Swim Diapers Reusable 3-Pack Cute Pattern Waterproof Toddler", 19.99),
            ("KiddoZone", "Diaper Cream Zinc Oxide 4oz Natural Organic Baby Rash Prevention", 12.99),
            ("SweetSlumber", "Training Pants 3T-4T 30-Count Boys Girls Pull Ups Potty Training", 24.99),
            ("BabyBloom", "Changing Pad Portable Waterproof Diaper Changing Clutch Travel", 16.99),
            ("ParentPick", "Diaper Pail Odor Lock 20L Hands Free Trash Can Refill Rings 2-Pack", 44.99),
        ],
        "Baby Gear": [
            ("BabyJoy", "Stroller Lightweight Compact Fold 4-Wheel Shock Absorb All Terrain", 249.99),
            ("LittleStars", "Baby Carrier Ergonomical Front Back Pack Infant Newborn Hip Seat", 69.99),
            ("TinyTot", "Car Seat Infant Convertible 5-65lbs Rear Facing Baby Travel System", 299.99),
            ("NurtureBaby", "Playpen 6-Panel Foldable Activity Center Baby Fence Mesh Safety", 129.99),
            ("KiddoZone", "High Chair Convertible Baby 3-in-1 Toddler Booster Seat Adjustable", 149.99),
            ("SweetSlumber", "Baby Swing Soothing Vibration 10-Speed 8 Melodies Portable Plush", 119.99),
            ("BabyBloom", "Baby Monitor 5-Inch Video Camera Night Vision Two Way Audio Talk", 79.99),
            ("ParentPick", "Activity Center Stationary Walker 360 Degree Seat Music Lights Toy", 89.99),
        ],
        "Nursery": [
            ("BabyJoy", "Crib Convertible 4-in-1 Baby Crib Toddler Bed Daybed Canopy White", 299.99),
            ("LittleStars", "Changing Table Dresser Combo 6-Drawer Baby Dresser Changing Top", 349.99),
            ("TinyTot", "Glider Rocker Nursing Chair Padded Ottoman Comfort Reclining Fabric", 259.99),
            ("NurtureBaby", "Crib Mattress Firm Dual Sided Waterproof Breathable Toddler 52x28", 129.99),
            ("KiddoZone", "Nursery Hamper Laundry Basket Baby Large Wicker 40L Lid Collapsible", 34.99),
            ("SweetSlumber", "Mobile Crib Toy Wooden Hanging Musical Spiral Infant Sensory 5-In-1", 39.99),
            ("BabyBloom", "Night Light Kids Projector Starry Sky Ceiling Lamp Baby Sleep Soother", 29.99),
            ("ParentPick", "Sound Machine White Noise 6-Sound 10-Volume Baby Sleep Aid Timer", 34.99),
        ],
        "Baby Clothing": [
            ("BabyJoy", "Onesie Short Sleeve 5-Pack 100% Organic Cotton Baby Bodysuit 0-3M", 29.99),
            ("LittleStars", "Baby Sleep Sack Wearable Blanket 1.5 TOG Cotton Zip Up Swaddle 6-12M", 34.99),
            ("TinyTot", "Baby Romper Footed Overall Cute Animal Print Snap Closure 12-18M", 24.99),
            ("NurtureBaby", "Baby Hat and Booties Set Organic Cotton 3-Piece Knit Cap Socks Mittens", 19.99),
            ("KiddoZone", "Baby Pajama Set 2-Piece Long Sleeve Zip One Piece Cotton Footie 0-3M", 22.99),
            ("SweetSlumber", "Baby Swaddle Wrap Cotton Muslin 2-Pack Breathable Soft Blanket 47x47", 29.99),
            ("BabyBloom", "Toddler Pants Stretchy Pull On 4-Pack Cotton Joggers Elastic Waist 2T", 24.99),
            ("ParentPick", "Baby Shoe Soft Sole Crib Moccasin 0-6 Months Leather Newborn Gift", 18.99),
        ],
        "Kids Toys": [
            ("BabyJoy", "Musical Toy Piano Baby 2-4 Years 25-Key Keyboard Xylophone Drum Combo", 39.99),
            ("LittleStars", "Play Kitchen Set 40-Piece Wooden Kids Cooking Playset Toddler 3+", 79.99),
            ("TinyTot", "Stacking Blocks Toy 12-Piece Wood Rainbow Nesting Sorting Tower Baby", 22.99),
            ("NurtureBaby", "Stuffed Animal Soft Toy Teddy Bear 12-Inch Plush Hypoallergenic Huggable", 19.99),
            ("KiddoZone", "Play Dough Set 20-Pack 10oz Modeling Clay Non Toxic Vibrant Colors", 18.99),
            ("SweetSlumber", "Ride On Car 12V Electric Kids RC Buggy Battery Powered 2-Seat Radio", 249.99),
            ("BabyBloom", "Shape Sorter Baby 12-24 Months Cube 8 Geometric Shapes Sensory Box", 16.99),
            ("ParentPick", "Pull Along Toy Wood Caterpillar 12+ Months Duck Animal Walking String", 14.99),
        ],
        "Feeding": [
            ("BabyJoy", "Baby Bottle Set Glass 5oz 4-Pack Slow Flow Nipples Newborn Infant", 24.99),
            ("LittleStars", "Breast Pump Electric Double Hands Free Portable 2-Phase Expression", 159.99),
            ("TinyTot", "Sippy Cup 360 Spill Proof 10oz Straw Transition Baby 6+ Months 3-Pack", 18.99),
            ("NurtureBaby", "Baby Food Maker Steamer Blender 2-in-1 Fresh Puree Vegetable 4-Cup", 69.99),
            ("KiddoZone", "High Chair Baby Feeding Suction Plate Set 3-Piece Bowl Spoon Divided Tray", 29.99),
            ("SweetSlumber", "Baby Bib Set 6-Pack Waterproof Long Sleeve Smock Cartoon Animal Print", 21.99),
            ("BabyBloom", "Formula Dispenser 2-Compartment 12oz Baby Travel Milk Powder Container", 14.99),
            ("ParentPick", "Silicone Teether Baby 3-Pack BPA Free Fruit Shape 0-12 Months Gum Relief", 12.99),
        ],
    },
    "Health & Wellness": {
        "Vitamins & Supplements": [
            ("VitalLife", "Vitamin D3 5000 IU 240 Softgels Supports Immune Bone Health", 16.99),
            ("WellnessPlus", "Omega-3 Fish Oil 1200mg 200 Softgels EPA DHA Heart Brain Support", 24.99),
            ("NatureCure", "Probiotics 30 Billion CFU 60 Capsules Digestive Gut Health Immune", 22.99),
            ("PureHealth", "Magnesium Glycinate 400mg 120 Capsules Sleep Calm Recovery", 19.99),
            ("ActiveLife", "Protein Powder Whey Isolate 5lb Chocolate 25g Protein Low Carb", 69.99),
            ("HolisticCare", "Collagen Peptides 20oz Hydrolyzed Type I III Grass Fed Skin Joint", 34.99),
            ("NutriBest", "Melatonin 10mg 120 Tablets Fast Dissolve Sleep Aid Night Support", 14.99),
            ("ZenMed", "Multivitamin for Adults 180 Tablets Complete Daily A to Zinc Immune", 21.99),
        ],
        "First Aid": [
            ("VitalLife", "First Aid Kit 100-Piece Emergency Compact Medical Bag Supplies Home", 24.99),
            ("WellnessPlus", "Bandages Assorted 200-Pack Flexible Fabric Waterproof Adhesive Strips", 12.99),
            ("NatureCure", "Cold Compress Instant Reusable Ice Pack 6-Pack 5x7 Softgel", 16.99),
            ("PureHealth", "Digital Thermometer Rapid Read Infant Oral Armpit Rectal Battery", 14.99),
            ("ActiveLife", "Elastic Bandage Wrap 4-Inch 5-Yard 2-Pack Self Adhesive Support", 11.99),
            ("HolisticCare", "Antiseptic Spray 8oz First Aid Wound Cleanser Pain Relief 3-Pack", 15.99),
            ("NutriBest", "CPR Mask Rescue Breather Keychain Single Use Barrier Pocket Face", 9.99),
            ("ZenMed", "Hot Water Bottle 2L Rubber Traditional Bed Warmer Pain Relief Gray", 18.99),
        ],
        "Essential Oils": [
            ("VitalLife", "Lavender Essential Oil 4oz Pure Aromatherapy Grade Therapeutic", 19.99),
            ("WellnessPlus", "Tea Tree Essential Oil 4oz 100% Pure Melaleuca Skin Hair Nail", 17.99),
            ("NatureCure", "Peppermint Essential Oil 4oz Pure Aromatherapy Energy Focus", 16.99),
            ("PureHealth", "Eucalyptus Essential Oil 4oz Pure Aromatherapy Steam Room Diffuser", 15.99),
            ("ActiveLife", "Diffuser Essential Oil Aromatherapy Ultrasonic 300ml Cool Mist Humidifier", 34.99),
            ("HolisticCare", "Essential Oil Roller Set 5-Pack Lavender Peppermint Frankincense Lemon", 22.99),
            ("NutriBest", "Frankincense Essential Oil 2oz Pure Sacred Premium Grade Boswellia", 29.99),
            ("ZenMed", "Lemon Essential Oil 4oz Pure Bright Citrus Aroma Cleaning Natural", 14.99),
        ],
        "Massage & Relaxation": [
            ("VitalLife", "Massage Gun Deep Tissue Percussion 6-Speed 4 Heads Bluetooth", 99.99),
            ("WellnessPlus", "Foot Spa Bath Massager Heated Bubbles Vibration Water Fidget Hot", 49.99),
            ("NatureCure", "Neck Massager Shiatsu Kneading Heat Deep Tissue Back Pain Relief", 59.99),
            ("PureHealth", "Eye Mask Sleep Light Blocking Silk 3D Molded Contoured Cup Cooling", 19.99),
            ("ActiveLife", "Massage Oil Lavender Unscented 16oz Natural Plant Based Vegan", 14.99),
            ("HolisticCare", "Acupressure Mat 29x16 Pillow Set Back Pain Relief Spike Fabric", 34.99),
            ("NutriBest", "Hand Massager Finger Arthritis Relief Compression Heat Air Pressure", 44.99),
            ("ZenMed", "Aromatherapy Candle Soy Wax Lavender Relaxing Calming 8oz Gift Tin", 24.99),
        ],
        "Fitness Trackers": [
            ("VitalLife", "Smart Fitness Watch Heart Rate Blood Oxygen Sleep Monitor Waterproof", 179.99),
            ("WellnessPlus", "Fitness Tracker Activity Band Step Counter Calorie Heart Rate Monitor", 69.99),
            ("NatureCure", "Smart Ring Health Tracker Sleep Score Activity Ring Waterproof", 299.99),
            ("PureHealth", "Smart Scale Bluetooth Digital Body Fat BMI Analyzer Muscle Mass", 44.99),
            ("ActiveLife", "Pulse Oximeter Finger OLED Blood Oxygen Saturation Monitor SPO2", 19.99),
            ("HolisticCare", "Blood Pressure Monitor Upper Arm Automatic Digital 2-User 90 Memory", 39.99),
            ("NutriBest", "Sleep Tracker Under Mattress Pad Non Wearable Sleep Cycle Analyzer", 149.99),
            ("ZenMed", "Hearing Amplifier Personal Sound Amplifier Rechargeable In Ear Pair", 89.99),
        ],
        "Wellness": [
            ("VitalLife", "Foam Roller High Density 36x6 Muscle Recovery Massage Trigger Point", 29.99),
            ("WellnessPlus", "Humidifier Cool Mist 2.5L Bedroom Quiet 24hr Baby Office Uric", 39.99),
            ("NatureCure", "Air Purifier HEPA True HEPA 99.97% Allergen Dust Pollen Home 1400sqft", 149.99),
            ("PureHealth", "Salt Lamp Himalayan Pink Crystal 6-8lbs Natural Air Purifier Base", 34.99),
            ("ActiveLife", "Posture Corrector Adjustable Support Brace Upper Back Clavicle Men Women", 24.99),
            ("HolisticCare", "TENS Unit Muscle Stimulator 24-Mode Electric Massage Pain Relief Back", 44.99),
            ("NutriBest", "Compression Socks 20-30mmHg Knee High Support Travel Running Pregnancy", 19.99),
            ("ZenMed", "Eye Massager Heated Vibration Air Pressure 3D Compression Bluetooth", 69.99),
        ],
    },
    "Music & Media": {
        "Musical Instruments": [
            ("SoundWave", "Acoustic Guitar 6-String Full Size Dreadnought Spruce Top Natural", 199.99),
            ("MelodyPro", "Digital Piano 88-Key Weighted Hammer Action Keyboard Stand Bench", 599.99),
            ("TuneCraft", "Electric Violin 4-4 Full Size Solid Body Gloss Natural Beginner Kit", 299.99),
            ("BeatStreet", "Drum Set 5-Piece Complete Acoustic Junior Adult Hardware Cymbals", 449.99),
            ("AudioPhile", "Ukulele Soprano Mahogany 4-String Hawaiian 15-Inch Beginner Kit", 49.99),
            ("RhythmHouse", "Keyboard Synthesizer 61-Key USB MIDI Production Workstation", 349.99),
            ("StageMaster", "Harmonica 10-Hole Key of C Blues Professional Richter Tuning", 29.99),
            ("ChordVibe", "Flute Beginner Student C-Flat Nickel Silver Closed Hole 16-Key", 129.99),
        ],
        "Vinyl & CDs": [
            ("SoundWave", "Vinyl Record Taylor Swift Midnights 3AM Edition 2LP Album 33RPM", 39.99),
            ("MelodyPro", "Vinyl Record Fleetwood Mac Rumours 45th Anniversary 2LP Gatefold", 34.99),
            ("TuneCraft", "Vinyl Record The Beatles Abbey Road 50th Anniversary Remastered LP", 36.99),
            ("BeatStreet", "Vinyl Record Pink Floyd Dark Side of the Moon 50th Anniv Box Set", 49.99),
            ("AudioPhile", "CD Album Adele 30 Standard Edition Compact Disc 12 Tracks", 14.99),
            ("RhythmHouse", "Vinyl Record Miles Davis Kind of Blue 200g Audiophile 180g Press", 32.99),
            ("StageMaster", "CD Box Set Beethoven Complete Symphonies 5-Disc Berlin Philharmonic", 44.99),
            ("ChordVibe", "Vinyl Record Prince Purple Rain Original Soundtrack 1984 LP", 29.99),
        ],
        "Streaming Devices": [
            ("SoundWave", "Streaming Media Player 4K HDR Dolby Vision Wi-Fi 6 Voice Remote", 49.99),
            ("MelodyPro", "Streaming Stick 4K Ultra HD HDR 10+ Dolby Atmos Portable TV Dongle", 39.99),
            ("TuneCraft", "Smart TV Box Android 12 4K 8K USB 3.0 Bluetooth 5.0 Voice Search", 69.99),
            ("BeatStreet", "Digital Media Player Hi-Res Audio 32-bit DAC WiFi Bluetooth DSD AKM", 299.99),
            ("AudioPhile", "Bluetooth Receiver 5.3 Adapter TV Audio Transmitter AptX HD Low Latency", 29.99),
            ("RhythmHouse", "Screen Mirroring Dongle 4K AirPlay Chromecast Miracast Wireless Display", 44.99),
            ("StageMaster", "Gaming Media Player Pro 4K 120fps HDMI 2.1 Wi-Fi 6E Cloud Gaming", 149.99),
            ("ChordVibe", "Music Streamer Wi-Fi AirPlay 2 Chromecast Multi-Room HiFi DAC ESS", 499.99),
        ],
        "Karaoke": [
            ("SoundWave", "Karaoke Machine Portable Bluetooth 2 Wireless Microphones Indoor Outdoor", 129.99),
            ("MelodyPro", "Karaoke System Home DVD Player CDG Discs Dual Mic Input 100W Speakers", 249.99),
            ("TuneCraft", "Wireless Microphone Set Dual UHF Handheld Dynamic Mic with Receiver", 69.99),
            ("BeatStreet", "Karaoke Party Speaker 400W Multi-Color LED Light Pro Sound Subwoofer", 299.99),
            ("AudioPhile", "Microphone Clip On Lapel Lavalier Condenser 3.5mm Omnidirectional for Karaoke", 19.99),
            ("RhythmHouse", "Karaoke Mixer Audio Processor Echo Reverb Tone Control 2-Channel", 89.99),
            ("StageMaster", "Karaoke Subscription Card 12-Month Unlimited Songs 10000+ Tracks Card", 49.99),
            ("ChordVibe", "Bluetooth Microphone Handheld Wireless Karaoke Mic Speaker Built-in Echo", 39.99),
        ],
        "DJ Equipment": [
            ("SoundWave", "DJ Controller 2-Channel USB MIDI Mixer Serato DJ Lite Included", 249.99),
            ("MelodyPro", "Turntable Direct Drive Professional Manual 2-Speed DJ Vinyl Player", 499.99),
            ("TuneCraft", "DJ Headphones Over Ear Closed Back Foldable Monitor Mixing Isolation", 99.99),
            ("BeatStreet", "DJ Mixer 4-Channel Digital Mixer Built-in FX USB Audio Interface", 349.99),
            ("AudioPhile", "Active PA Speaker 12-Inch 1000W Professional Sound System 2-Way DJ", 299.99),
            ("RhythmHouse", "DJ Lighting System 4-Pack LED Par Can 18x12W RGBWA+UV Stage Wash DMX", 199.99),
            ("StageMaster", "DJ Case Laptop Stand Adjustable Folding Aluminum Universal Mixer Table", 89.99),
            ("ChordVibe", "Controller Case DJ Flight Hard Shell Water Resistant Foam Interior 21x15", 149.99),
        ],
    },
}

# Weights for event type distribution
EVENT_WEIGHTS = {
    "page_view": 0.50,
    "purchase": 0.10,
    "add_to_cart": 0.10,
    "remove_from_cart": 0.05,
    "email_open": 0.03,
    "email_click": 0.02,
    "wishlist_add": 0.05,
}

SEGMENTS = ["high_value", "bargain_hunter", "new_user", "lapsed", "cart_abandoner", "brand_loyalist", "window_shopper", "power_user"]

# ── Category-relevant product image pools ──────────────────────────────
# Each category has a pool of verified Unsplash photo IDs that visually
# represent that category (gadgets for Electronics, fitness for Sports, etc.)
# Images are 400x300 crop via Unsplash CDN. A stable hash of the product_id
# deterministically selects which image from the pool a product gets.
# Keys match both the long PRODUCT_DEFINITIONS names and the short DB names.
SUBCATEGORY_IMAGE_POOL: dict[str, list[str]] = {
    "Smartphones": [
        "photo-1511707171634-5f897ff02aa9",
        "photo-1598327105666-5b89351aff97",
        "photo-1601784551446-20c9e07cdbdb",
        "photo-1512499617640-c74ae3a79d37",
        "photo-1591337676887-a217a6970a8a",
        "photo-1616348436168-de43ad0db179",
        "photo-1621330396173-e41b1cafd17f",
        "photo-1593642632823-8f785ba67e45",
    ],
    "Laptops": [
        "photo-1496181133206-80ce9b88a853",
        "photo-1517694712202-14dd9538aa97",
        "photo-1498050108023-c5249f4df085",
        "photo-1517336714731-489689fd1ca8",
        "photo-1460925895917-afdab827c52f",
        "photo-1541807084-5c52b6b3adef",
        "photo-1603302576837-37561b2e2302",
        "photo-1525547719571-a2d4ac8945e2",
    ],
    "Headphones": [
        "photo-1505740420928-5e560c06d30e",
        "photo-1487215078519-e21cc028cb29",
        "photo-1484704849700-f032a568e944",
        "photo-1583394838336-acd977736f90",
        "photo-1590658268037-6bf12165a8df",
        "photo-1546435770-a3e426bf472b",
        "photo-1550684848-fac1c5b4e853",
        "photo-1572569511254-d8f925fe2cbb",
    ],
    "Tablets": [
        "photo-1585790050230-5dd28404ccb9",
        "photo-1544724569-5f546fd6f2b5",
        "photo-1568430462989-44163eb1752f",
        "photo-1506729623306-b5a934d88b53",
        "photo-1561154464-82e9adf32764",
        "photo-1519389950473-47ba0277781c",
        "photo-1531297484001-80022131f5a1",
        "photo-1526738549149-8e07eca6c147",
    ],
    "Smartwatches": [
        "photo-1523275335684-37898b6baf30",
        "photo-1544117519-31a4b719223d",
        "photo-1434056886845-dac89ffe9b56",
        "photo-1546868871-7041f2a55e12",
        "photo-1617043786394-f977fa12eddf",
        "photo-1579586337278-3befd40fd17a",
        "photo-1550009158-9ebf69173e03",
        "photo-1516321318423-f06f85e504b3",
    ],
    "Cameras": [
        "photo-1516035069371-29a1b244cc32",
        "photo-1502920514313-52581002a659",
        "photo-1519183071298-a2962feb14f4",
        "photo-1495707902641-75cac588d2e9",
        "photo-1520390138845-fd2d229dd553",
        "photo-1510127034890-ba27508e9f1c",
        "photo-1520549233664-03f65c1d1327",
        "photo-1555066931-4365d14bab8c",
    ],
    "Cables & Chargers": [
        "photo-1585336261022-680e295ce3fe",
        "photo-1600880292203-757bb62b4baf",
        "photo-1520209759809-a9bcb6cb3241",
        "photo-1615526675159-e248c3021d3f",
        "photo-1611224923853-80b023f02d71",
        "photo-1518444065439-e933c06ce9cd",
        "photo-1588872657578-7efd1f1555ed",
        "photo-1601524909162-ae8725290836",
    ],
    "Speakers": [
        "photo-1608043152269-423dbba4e7e1",
        "photo-1544383835-bda2bc66a55d",
        "photo-1558089687-f282ffcbc126",
        "photo-1591047139829-d91aecb6caea",
        "photo-1545454675-3531b543be5d",
        "photo-1487058792275-0ad4aaf24ca7",
    ],
    "Vitamins & Supplements": [
        "photo-1670850757896-e1b6c3e311ea",
        "photo-1624362772755-4d5843e67047",
        "photo-1732900293895-233f769299b3",
        "photo-1559087316-6b27308e53f6",
        "photo-1528272252360-5efd274e36fb",
        "photo-1729701028046-2bd5b736a6d7",
        "photo-1664786908163-85ca46f85138",
        "photo-1592323818181-f9b967ff537c",
        "photo-1648139346494-2b961c5a2bb7",
        "photo-1732900490015-a5167a642998",
        "photo-1670850756917-8ed6c2a71e12",
    ],
    "First Aid": [
        "photo-1684655570542-55afe322a74b",
        "photo-1619794555233-e563edf91173",
        "photo-1765996796562-ce301df337a0",
        "photo-1624638760852-8ede1666ab07",
        "photo-1600091474842-83bb9c05a723",
        "photo-1563260324-5ebeedc8af7c",
        "photo-1564144573017-8dc932e0039e",
        "photo-1566889035559-b14ef9d4c365",
    ],
    "Essential Oils": [
        "photo-1671493234254-15fc6c91aa87",
        "photo-1676852148076-7a92002419f3",
        "photo-1560521166-117ca72366bd",
        "photo-1671493229066-f36e86b35841",
        "photo-1671493235081-5842463637cd",
        "photo-1605040056130-38d9faad3534",
        "photo-1671493234279-57ef0c8f34e6",
        "photo-1608571423539-e951b9b3871e",
        "photo-1671493233620-cc6a416561aa",
        "photo-1560521166-e4af6324303d",
        "photo-1671493228013-328eb74b767b",
    ],
    "Massage & Relaxation": [
        "photo-1519824145371-296894a0daa9",
        "photo-1639162906614-0603b0ae95fd",
        "photo-1696841212541-449ca29397cc",
        "photo-1706795033728-9232ef548a16",
        "photo-1712638932314-e2b185ca0930",
        "photo-1611073615830-9f76902c10fe",
        "photo-1741522509438-a120c0bb5e88",
        "photo-1745327883508-b6cd32e5dde5",
        "photo-1741522509407-41cfe73b0b75",
        "photo-1544161515-4ab6ce6db874",
    ],
    "Fitness Trackers": [
        "photo-1575311373937-040b8e1fd5b6",
        "photo-1579721840641-7d0e67f1204e",
        "photo-1434494817513-cc112a976e36",
        "photo-1596236100223-f3c656de3038",
        "photo-1508685096489-7aacd43bd3b1",
        "photo-1434494878577-86c23bcb06b9",
        "photo-1544117519-31a4b719223d",
        "photo-1597923709001-5a061c88418d",
        "photo-1503328427499-d92d1ac3d174",
        "photo-1660844817855-3ecc7ef21f12",
        "photo-1696688713460-de12ac76ebc6",
        "photo-1576243345690-4e4b79b63288",
        "photo-1517502474097-f9b30659dadb",
    ],
    "Wellness": [
        "photo-1740479050129-7fef21254518",
        "photo-1762331658154-8aa265ca21e5",
        "photo-1548966268-b978ed7b2e83",
        "photo-1579126038374-6064e9370f0f",
        "photo-1579126096454-0029977dcac1",
        "photo-1602520628350-fbf9db1f02ae",
        "photo-1556911073-a517e752729c",
        "photo-1635367216109-aa3353c0c22e",
        "photo-1579722820308-d74e571900a9",
        "photo-1758274525887-d95d19269f76",
        "photo-1770269845802-99a69d9a29a9",
        "photo-1666979289472-96e6d3245b84",
    ],
    "Fitness Equipment": [
        "photo-1722925541311-2117dfa21fe3",
        "photo-1674834727206-4bc272bfd8da",
        "photo-1619550158663-d1a3dc5f064f",
        "photo-1632077804406-188472f1a810",
        "photo-1591291621164-2c6367723315",
        "photo-1637430308606-86576d8fef3c",
        "photo-1576678927484-cc907957088c",
        "photo-1639511205273-7af2f8805d10",
    ],
    "Sportswear": [
        "photo-1649520937981-763d6a14de7d",
        "photo-1655089131279-8029e8a21ac6",
        "photo-1552066379-e7bfd22155c5",
        "photo-1696300064576-c072b92f4c55",
        "photo-1737748612418-e39bcd6503a2",
        "photo-1540254597053-3901b858d40f",
        "photo-1637666532931-b835a227b955",
        "photo-1605235456089-289f866adef2",
    ],
    "Yoga": [
        "photo-1646239646963-b0b9be56d6b5",
        "photo-1637157216470-d92cd2edb2e8",
        "photo-1718862403436-616232ec6005",
        "photo-1641913640860-ab4c2bfb2bb0",
        "photo-1579016749257-3f5205b5e5ae",
        "photo-1575052814086-f385e2e2ad1b",
        "photo-1566501206188-5dd0cf160a0e",
        "photo-1600881333168-2ef49b341f30",
    ],
    "Cycling": [
        "photo-1532298229144-0ec0c57515c7",
        "photo-1497515098781-e965764ab601",
        "photo-1505705694340-019e1e335916",
        "photo-1576435728678-68d0fbf94e91",
        "photo-1485965120184-e220f721d03e",
        "photo-1534146789009-76ed5060ec70",
        "photo-1541625602330-2277a4c46182",
        "photo-1452573992436-6d508f200b30",
    ],
    "Camping Gear": [
        "photo-1496080174650-637e3f22fa03",
        "photo-1510312305653-8ed496efae75",
        "photo-1504280390367-361c6d9f38f4",
        "photo-1504851149312-7a075b496cc7",
        "photo-1631635589499-afd87d52bf64",
        "photo-1478131143081-80f7f84ca84d",
        "photo-1532339142463-fd0a8979791a",
        "photo-1602391833977-358a52198938",
    ],
    "Water Bottles": [
        "photo-1649345867132-e8bd35bedf76",
        "photo-1516116189403-10c54c714a28",
        "photo-1648313021325-d81f28d57824",
        "photo-1618354691249-18772bbac3a5",
        "photo-1649888254873-d9870ee286ee",
        "photo-1680265346124-ba1b82b19d5f",
        "photo-1561041695-d2fadf9f318c",
        "photo-1553564552-02656d6a2390",
    ],
    "Gym Bags": [
        "photo-1448582649076-3981753123b5",
        "photo-1525103504173-8dc1582c7430",
        "photo-1708622833152-924c6e364138",
        "photo-1774560745344-78667b3594a7",
        "photo-1672223303533-05fddcbf6e6c",
        "photo-1531938716357-224c16b5ace3",
        "photo-1763144536786-976af447e738",
        "photo-1679274800600-d41929f429eb",
    ],
    "Board Games": [
        "photo-1703248184387-f6b2cbe1c981",
        "photo-1703925153100-43afda8b6506",
        "photo-1672888434432-e7d98ae9abb2",
        "photo-1741790009218-d0cc7440a3c2",
        "photo-1705043859787-93d64c9e3c01",
        "photo-1771329967756-db1459b43870",
        "photo-1710131991511-f53b74a3e3a7",
        "photo-1715748141794-3d6a393675ae",
    ],
    "Puzzles": [
        "photo-1730804518415-75297e8d2a41",
        "photo-1526566661780-1a67ea3c863e",
        "photo-1586527155314-1d25428324ff",
        "photo-1709399610754-921b7a9ef3b7",
        "photo-1684773585761-fde68b4ece42",
        "photo-1605712916066-e143c317df72",
        "photo-1494059980473-813e73ee784b",
        "photo-1612611741189-a9b9eb01d515",
    ],
    "Action Figures": [
        "photo-1623039902375-29258147f39e",
        "photo-1635875560469-2b94b774c187",
        "photo-1550479023-2a811e19dfd3",
        "photo-1557985594-29f3ad9f5134",
        "photo-1578632767115-351597cf2477",
        "photo-1606663889134-b1dedb5ed8b7",
        "photo-1623039978462-d01b0b1cad70",
        "photo-1623040289381-20c625fb9f2f",
    ],
    "Building Sets": [
        "photo-1620309668391-26ac1c90f61b",
        "photo-1543878636-41918458581d",
        "photo-1573952106639-694daec2b88a",
        "photo-1493217465235-252dd9c0d632",
        "photo-1728550958364-1e0348a09508",
        "photo-1636314229901-61b1c1da1675",
        "photo-1759147893749-7c92a92cd9d1",
        "photo-1631106254201-ffbee2305c5b",
    ],
    "Educational Toys": [
        "photo-1773507119465-99a51f58cdd3",
        "photo-1558907353-ceb54f3882ed",
        "photo-1683234803972-cc87e51d4af1",
        "photo-1596461404969-9ae70f2830c1",
        "photo-1718306201865-cae4a08311fe",
        "photo-1548690596-f1722c190938",
        "photo-1548175551-1edaea7bbf0d",
        "photo-1611957082126-061f655ef1fb",
    ],
    "Outdoor Play": [
        "photo-1596997000103-e597b3ca50df",
        "photo-1634608874538-443b84f7b06b",
        "photo-1552537595-b30edb7afd9d",
        "photo-1711369093144-2ada6e035a84",
        "photo-1774879467955-28d1003cae31",
        "photo-1766104959444-f23e3a2f3f9c",
        "photo-1767080661512-41eba6bdac1c",
        "photo-1638202951770-2240942c7d1c",
    ],
    "Video Games": [
        "photo-1486572788966-cfd3df1f5b42",
        "photo-1600861194942-f883de0dfe96",
        "photo-1572537577590-ac6a88150100",
        "photo-1580234811497-9df7fd2f357e",
        "photo-1604846887565-640d2f52d564",
        "photo-1612287230202-1ff1d85d1bdf",
        "photo-1638581777063-bf3ed0496c67",
        "photo-1763986365305-109ad3ddbf2b",
    ],
}

# Species-specific pools for Pet Supplies so cat products never show a dog photo
# and vice-versa. All IDs species-confirmed and verified live (HTTP 200, image/jpeg).
PET_CAT_IMAGE_POOL: list[str] = [
    "photo-1514888286974-6c03e2ca1dba",
    "photo-1456677698485-dceeec22c7fc",
    "photo-1726044781679-7c3f20a185ec",
    "photo-1556799483-8a3c48110b63",
    "photo-1558349768-279a6d352b66",
    "photo-1520772342158-af0a83de0372",
    "photo-1519468863299-05e2f6f6df56",
    "photo-1563263330-52f46a1b8de5",
    "photo-1553366735-5452d07f2c20",
    "photo-1557312309-a08700b45135",
    "photo-1512200331909-44d741611b43",
    "photo-1526837108083-1cee44e4abd0",
    "photo-1557743952-b088259408a2",
    "photo-1585373683920-671438c82bfa",
    "photo-1631307494857-fa85ac2c6c38",
    "photo-1548546738-8509cb246ed3",
    "photo-1606491048802-8342506d6471",
    "photo-1597838816882-4435b1977fbe",
    "photo-1571570703598-39eb580a0329",
    "photo-1572171572779-e93ec53b8024",
    "photo-1548366086-7f1b76106622",
    "photo-1580784355694-0d5295dcc007",
    "photo-1599889959407-598566c6e1f1",
    "photo-1644237698898-f0b63b5ce54e",
    "photo-1560145393-2f79d01cabc5",
    "photo-1608032364895-0da67af36cd2",
    "photo-1548724582-1216ec5351ce",
    "photo-1506891536236-3e07892564b7",
    "photo-1518791841217-8f162f1e1131",
    "photo-1573865526739-10659fec78a5",
    "photo-1519052537078-e6302a4968d4",
    "photo-1592194996308-7b43878e84a6",
    "photo-1533738363-b7f9aef128ce",
    "photo-1529778873920-4da4926a72c2",
    "photo-1472491235688-bdc81a63246e",
    "photo-1542665348-1df255e08297",
    "photo-1496284575094-d5b92db3890d",
    "photo-1567270671170-fdc10a5bf831",
    "photo-1495360010541-f48722b34f7d",
    "photo-1561406186-fa3708c3c15c",
    "photo-1520560321666-4b36560e7979",
    "photo-1542736705-53f0131d1e98",
    "photo-1545919888-f8a7bb889672",
    "photo-1530991671072-ac4f81c2c3c1",
    "photo-1496890666403-e6cf521841e6",
]

PET_DOG_IMAGE_POOL: list[str] = [
    "photo-1615233500064-caa995e2f9dd",
    "photo-1602241628512-459cdd3234fe",
    "photo-1693615775129-f2004d6e3e0b",
    "photo-1637098063179-d73d8034621c",
    "photo-1558788353-f76d92427f16",
    "photo-1588022274642-f238f77ec193",
    "photo-1513549054-cb3611a004fe",
    "photo-1633722715463-d30f4f325e24",
    "photo-1561037404-61cd46aa615b",
    "photo-1598133894008-61f7fdb8cc3a",
    "photo-1544568100-847a948585b9",
    "photo-1568572933382-74d440642117",
    "photo-1583511655857-d19b40a7a54e",
    "photo-1516734212186-a967f81ad0d7",
    "photo-1552053831-71594a27632d",
    "photo-1518717758536-85ae29035b6d",
    "photo-1548199973-03cce0bbc87b",
    "photo-1517849845537-4d257902454a",
    "photo-1560807707-8cc77767d783",
    "photo-1647179924662-13b7bc73a886",
    "photo-1596490634801-c536934af56e",
    "photo-1535930749574-1399327ce78f",
    "photo-1557495235-340eb888a9fb",
    "photo-1583511666372-62fc211f8377",
    "photo-1587300003388-59208cc962cb",
    "photo-1543466835-00a7907e9de1",
]

CATEGORY_IMAGE_POOL: dict[str, list[str]] = {
    "Electronics": [
        "photo-1519389950473-47ba0277781c",
        "photo-1498050108023-c5249f4df085",
        "photo-1505740420928-5e560c06d30e",
        "photo-1523275335684-37898b6baf30",
        "photo-1555066931-4365d14bab8c",
        "photo-1516321318423-f06f85e504b3",
        "photo-1550009158-9ebf69173e03",
        "photo-1487058792275-0ad4aaf24ca7",
        "photo-1526738549149-8e07eca6c147",
        "photo-1601524909162-ae8725290836",
        "photo-1502920514313-52581002a659",
        "photo-1517694712202-14dd9538aa97",
        "photo-1531297484001-80022131f5a1",
    ],
    "Clothing": [
        "photo-1523381210434-271e8be1f52b",
        "photo-1490481651871-ab68de25d43d",
        "photo-1460353581641-37baddab0fa2",
        "photo-1556905055-8f358a7a47b2",
        "photo-1568252542512-9fe8fe9c87bb",
        "photo-1593030761757-71fae45fa0e7",
        "photo-1576566588028-4147f3842f27",
        "photo-1492707892479-7bc8d5a4ee93",
        "photo-1485968579580-b6d095142e6e",
        "photo-1507413245164-6160d8298b31",
        "photo-1525507119028-ed4c629a60a3",
        "photo-1529139574466-a303027c1d8b",
        "photo-1496345875659-11f7dd282d1d",
        "photo-1509631179647-0177331693ae",
        "photo-1521572163474-6864f9cf17ab",
        "photo-1542291026-7eec264c27ff",
        "photo-1511556820780-d912e42b4980",
        "photo-1541099649105-f69ad21f3246",
        "photo-1548036328-c9fa89d128fa",
        "photo-1445205170230-053b83016050",
        "photo-1434389677669-e08b4cac3105",
        "photo-1441986300917-64674bd600d8",
        "photo-1490114538077-0a7f8cb49891",
        "photo-1441984904996-e0b6ba687e04",
        "photo-1449247709967-d4461a6a6103",
        "photo-1516826957135-700dedea698c",
        "photo-1509316975850-ff9c5deb0cd9",
        "photo-1558769132-cb1aea458c5e",
        "photo-1566207274740-0f8cf6b7d5a5",
        "photo-1552374196-c4e7ffc6e126",
        "photo-1591047139829-d91aecb6caea",
        "photo-1544441893-675973e31985",
        "photo-1525171254930-643fc658b64e",
        "photo-1572804013309-59a88b7e92f1",
        "photo-1543807535-eceef0bc6599",
        "photo-1563630423918-b58f07336ac9",
        "photo-1596755094514-f87e34085b2c",
        "photo-1608231387042-66d1773070a5",
        "photo-1618354691373-d851c5c3a990",
        "photo-1620799140408-edc6dcb6d633",
        "photo-1617137968427-85924c800a22",
        "photo-1595777457583-95e059d581b8",
        "photo-1593032465175-481ac7f401a0",
        "photo-1584273143981-41c073dfe8f8",
        "photo-1594633312681-425c7b97ccd1",
        "photo-1603252109303-2751441dd157",
        "photo-1566150905458-1bf1fc113f0d",
        "photo-1576871337622-98d48d1cf531",
        "photo-1598300042247-d088f8ab3a91",
        "photo-1527082395-e939b847da0d",
        "photo-1551028719-00167b16eac5",
        "photo-1602293589930-45aad59ba3ab",
        "photo-1594608661623-aa0bd3a69d98",
        "photo-1601924994987-69e26d50dc26",
        "photo-1557787163-1635e2efb160",
        "photo-1515886657613-9f3515b0c78f",
        "photo-1519238263530-99bdd11df2ea",
        "photo-1611080626919-7cf5a9dbab5b",
        "photo-1526510747491-58f928ec870f",
    ],
    "Home & Kitchen": [
        "photo-1556909114-f6e7ad7d3136",
        "photo-1556909172-54557c7e4fb7",
        "photo-1484154218962-a197022b5858",
        "photo-1484101403633-562f891dc89a",
        "photo-1493663284031-b7e3aefcae8e",
        "photo-1555041469-a586c61ea9bc",
        "photo-1513694203232-719a280e022f",
        "photo-1493809842364-78817add7ffb",
        "photo-1505692952047-1a78307da8f2",
        "photo-1512917774080-9991f1c4c750",
        "photo-1560448204-e02f11c3d0e2",
        "photo-1600585154340-be6161a56a0c",
        "photo-1556911220-bff31c812dba",
        "photo-1615874959474-d609969a20ed",
        "photo-1551218808-94e220e084d2",
        "photo-1616486338812-3dadae4b4ace",
        "photo-1567016432779-094069958ea5",
        "photo-1594026112284-02bb6f3352fe",
        "photo-1631679706909-1844bbd07221",
        "photo-1540518614846-7eded433c457",
        "photo-1618221195710-dd6b41faaea6",
        "photo-1586023492125-27b2c045efd7",
        "photo-1502672260266-1c1ef2d93688",
        "photo-1505693416388-ac5ce068fe85",
        "photo-1507652313519-d4e9174996dd",
        "photo-1522708323590-d24dbb6b0267",
        "photo-1505691938895-1758d7feb511",
        "photo-1513506003901-1e6a229e2d15",
        "photo-1567016376408-0226e4d0c1ea",
        "photo-1615529182904-14819c35db37",
        "photo-1508873696983-2dfd5898f08b",
        "photo-1584568694244-14fbdf83bd30",
        "photo-1507089947368-19c1da9775ae",
        "photo-1642463002682-a63e802cbc3f",
        "photo-1515442094343-9a10f85a4b79",
        "photo-1560448204-603b3fc33ddc",
        "photo-1616137466211-f939a420be84",
        "photo-1540574163026-643ea20ade25",
        "photo-1618220179428-22790b461013",
        "photo-1505693314120-0d443867891c",
        "photo-1617104678098-de229db51175",
        "photo-1631049307264-da0ec9d70304",
        "photo-1617806118233-18e1de247200",
        "photo-1615875605825-5eb9bb5d52ac",
        "photo-1538688525198-9b88f6f53126",
        "photo-1567538096630-e0c55bd6374c",
        "photo-1583947215259-38e31be8751f",
        "photo-1616627547584-bf28cee262db",
        "photo-1570222094114-d054a817e56b",
        "photo-1654064754916-e3edeb09c042",
        "photo-1618506408870-64d8bec48248",
        "photo-1740803292814-13d2e35924c3",
        "photo-1594213114663-d94db9b17125",
        "photo-1584990347193-6bebebfeaeee",
        "photo-1602533438197-c9c47ae4b258",
        "photo-1593618229012-8aaad1cfefc3",
        "photo-1609467334293-030ac6448fd8",
        "photo-1633536705119-bcc37bf6c84e",
        "photo-1528740561666-dc2479dc08ab",
        "photo-1550963295-019d8a8a61c5",
        "photo-1689127903369-aef916b0c40d",
        "photo-1763025747123-bb3a2e3a5ac3",
        "photo-1568146687696-427782f92379",
        "photo-1536626071326-72cd66f4b28f",
        "photo-1669500708975-a73bbbc70a90",
    ],
    "Books": [
        "photo-1512820790803-83ca734da794",
        "photo-1524995997946-a1c2e315a42f",
        "photo-1507842217343-583bb7270b66",
        "photo-1456513080510-7bf3a84b82f8",
        "photo-1481627834876-b7833e8f5570",
        "photo-1491841573634-28140fc7ced7",
        "photo-1532012197267-da84d127e765",
        "photo-1506880018603-83d5b814b5a6",
        "photo-1512070679279-8988d32161be",
        "photo-1521737604893-d14cc237f11d",
        "photo-1432821596592-e2c18b78144f",
        "photo-1516979187457-637abb4f9353",
        "photo-1544716278-ca5e3f4abd8c",
        "photo-1495446815901-a7297e633e8d",
        "photo-1524578271613-d550eacf6090",
        "photo-1519681393784-d120267933ba",
        "photo-1473187983305-f615310e7daa",
        "photo-1450101499163-c8848c66ca85",
        "photo-1509021436665-8f07dbf5bf1d",
        "photo-1544947950-fa07a98d237f",
        "photo-1484417894907-623942c8ee29",
        "photo-1457369804613-52c61a468e7d",
        "photo-1513475382585-d06e58bcb0e0",
        "photo-1535905557558-afc4877a26fc",
        "photo-1478860409698-8707f313ee8b",
        "photo-1517841905240-472988babdf9",
        "photo-1519682337058-a94d519337bc",
        "photo-1541963463532-d68292c34b19",
        "photo-1535398089889-dd807df1dfaa",
        "photo-1519810755548-39cd217da494",
        "photo-1522199755839-a2bacb67c546",
        "photo-1543002588-bfa74002ed7e",
        "photo-1553729459-efe14ef6055d",
        "photo-1521123845560-14093637aa7d",
        "photo-1525253086316-d0c936c814f8",
        "photo-1503708928676-1cb796a0891e",
        "photo-1495474472287-4d71bcdd2085",
        "photo-1485988412941-77a35537dae4",
        "photo-1494548162494-384bba4ab999",
        "photo-1521587760476-6c12a4b040da",
        "photo-1589998059171-988d887df646",
        "photo-1520869562399-e772f042f422",
        "photo-1606326608606-aa0b62935f2b",
        "photo-1505686994434-e3cc5abf1330",
        "photo-1514846326710-096e4a8035e0",
    ],
    "Sports & Outdoors": [
        "photo-1517838277536-f5f99be501cd",
        "photo-1571902943202-507ec2618e8f",
        "photo-1552674605-db6ffd4facb5",
        "photo-1571019613454-1cb2f99b2d8b",
        "photo-1534438327276-14e5300c3a48",
        "photo-1511988617509-a57c8a288659",
        "photo-1517649763962-0c623066013b",
        "photo-1476480862126-209bfaa8edc8",
        "photo-1517457373958-b7bdd4587205",
        "photo-1541534741688-6078c6bfb5c5",
        "photo-1517963879433-6ad2b056d712",
        "photo-1517836357463-d25dfeac3438",
        "photo-1526506118085-60ce8714f8c5",
        "photo-1540497077202-7c8a3999166f",
        "photo-1554284126-aa88f22d8b74",
        "photo-1571731956672-f2b94d7dd0cb",
        "photo-1538805060514-97d9cc17730c",
        "photo-1550258987-190a2d41a8ba",
        "photo-1599058917212-d750089bc07e",
        "photo-1581009146145-b5ef050c2e1e",
        "photo-1519861531473-9200262188bf",
        "photo-1543163521-1bf539c55dd2",
        "photo-1593079831268-3381b0db4a77",
        "photo-1541534401786-2077eed87a74",
        "photo-1546483875-ad9014c88eba",
        "photo-1562774053-701939374585",
        "photo-1565992441121-4367c2967103",
        "photo-1599058917765-a780eda07a3e",
        "photo-1532029837206-abbe2b7620e3",
        "photo-1556817411-31ae72fa3ea0",
        "photo-1553284965-83fd3e82fa5a",
        "photo-1561214115-f2f134cc4912",
        "photo-1461896836934-ffe607ba8211",
        "photo-1550254478-ead40cc54513",
        "photo-1591115765373-5207764f72e7",
        "photo-1548690312-e3b507d8c110",
        "photo-1518611012118-696072aa579a",
        "photo-1574680096145-d05b474e2155",
        "photo-1531834685032-c34bf0d84c77",
        "photo-1584735935682-2f2b69dff9d2",
        "photo-1530549387789-4c1017266635",
        "photo-1547592180-85f173990554",
        "photo-1522312346375-d1a52e2b99b3",
        "photo-1571508601891-ca5e7a713859",
        "photo-1544367567-0f2fcb009e0b",
        "photo-1521572163474-6864f9cf17ab",
        "photo-1579952363873-27f3bade9f55",
        "photo-1605296867304-46d5465a13f1",
        "photo-1583454110551-21f2fa2afe61",
    ],
    "Sports": [
        "photo-1517838277536-f5f99be501cd",
        "photo-1571902943202-507ec2618e8f",
        "photo-1552674605-db6ffd4facb5",
        "photo-1571019613454-1cb2f99b2d8b",
        "photo-1534438327276-14e5300c3a48",
        "photo-1511988617509-a57c8a288659",
        "photo-1517649763962-0c623066013b",
        "photo-1476480862126-209bfaa8edc8",
        "photo-1517457373958-b7bdd4587205",
        "photo-1541534741688-6078c6bfb5c5",
    ],
    "Beauty & Personal Care": [
        "photo-1487412912498-0447578fcca8",
        "photo-1570172619644-dfd03ed5d881",
        "photo-1556228720-195a672e8a03",
        "photo-1596755389378-c31d21fd1273",
        "photo-1631730486572-226d1f595b68",
        "photo-1748543668676-ea8241cb3886",
        "photo-1631730486784-5456119f69ae",
        "photo-1653784097013-786a8965ea3b",
        "photo-1583209814683-c023dd293cc6",
        "photo-1629198688000-71f23e745b6e",
        "photo-1613803745799-ba6c10aace85",
        "photo-1667266543254-505cf5b16ec4",
        "photo-1718490953028-021d352b14fd",
        "photo-1636740599648-ae84f705fc2e",
        "photo-1629380108599-ea06489d66f5",
        "photo-1600634999623-864991678406",
        "photo-1601049413574-214d105b26e4",
        "photo-1631730359585-38a4935cbec4",
        "photo-1633793566189-8e9fe6f817fc",
        "photo-1596462502278-27bfdc403348",
        "photo-1620916566398-39f1143ab7be",
        "photo-1571781926291-c477ebfd024b",
        "photo-1522335789203-aabd1fc54bc9",
        "photo-1512496015851-a90fb38ba796",
        "photo-1598440947619-2c35fc9aa908",
        "photo-1556228578-8c89e6adf883",
        "photo-1522337660859-02fbefca4702",
        "photo-1562322140-8baeececf3df",
        "photo-1526947425960-945c6e72858f",
        "photo-1541643600914-78b084683601",
        "photo-1594035910387-fea47794261f",
        "photo-1588405748880-12d1d2a59f75",
        "photo-1556228453-efd6c1ff04f6",
        "photo-1526045478516-99145907023c",
        "photo-1522336572468-97b06e8ef143",
        "photo-1487412720507-e7ab37603c6f",
        "photo-1512036666432-2181c1f26420",
        "photo-1519415943484-9fa1873496d4",
        "photo-1611085583191-a3b181a88401",
        "photo-1540555700478-4be289fbecef",
        "photo-1600334129128-685c5582fd35",
        "photo-1559599101-f09722fb4948",
        "photo-1596178065887-1198b6148b2b",
        "photo-1595950653106-6c9ebd614d3a",
        "photo-1616683693504-3ea7e9ad6fec",
        "photo-1607779097040-26e80aa78e66",
        "photo-1572726729207-a78d6feb18d7",
        "photo-1511174511562-5f7f18b874f8",
        "photo-1571875257727-256c39da42af",
        "photo-1601612628452-9e99ced43524",
        "photo-1521783988139-89397d761dce",
        "photo-1586495777744-4413f21062fa",
        "photo-1560769629-975ec94e6a86",
        "photo-1495214783159-3503fd1b572d",
        "photo-1611930022073-b7a4ba5fcccd",
    ],
    "Beauty": [
        "photo-1487412912498-0447578fcca8",
        "photo-1570172619644-dfd03ed5d881",
        "photo-1556228720-195a672e8a03",
        "photo-1596755389378-c31d21fd1273",
        "photo-1631730486572-226d1f595b68",
        "photo-1748543668676-ea8241cb3886",
        "photo-1631730486784-5456119f69ae",
        "photo-1653784097013-786a8965ea3b",
        "photo-1583209814683-c023dd293cc6",
        "photo-1629198688000-71f23e745b6e",
        "photo-1613803745799-ba6c10aace85",
        "photo-1667266543254-505cf5b16ec4",
        "photo-1718490953028-021d352b14fd",
        "photo-1636740599648-ae84f705fc2e",
        "photo-1629380108599-ea06489d66f5",
        "photo-1600634999623-864991678406",
        "photo-1601049413574-214d105b26e4",
        "photo-1631730359585-38a4935cbec4",
        "photo-1633793566189-8e9fe6f817fc",
    ],
    "Toys & Games": [
        "photo-1596464716127-f2a82984de30",
        "photo-1519331379826-f10be5486c6f",
        "photo-1593085512500-5d55148d6f0d",
        "photo-1587654780291-39c9404d746b",
        "photo-1566577134770-3d85bb3a9cc4",
        "photo-1563941406054-949225931d52",
        "photo-1730804518415-75297e8d2a41",
        "photo-1629760946220-5693ee4c46ac",
        "photo-1612611741189-a9b9eb01d515",
        "photo-1588591795084-1770cb3be374",
        "photo-1494059980473-813e73ee784b",
        "photo-1611329857570-f02f340e7378",
        "photo-1677188010559-0667a1ed33a0",
        "photo-1612385763901-68857dd4c43c",
        "photo-1637120149073-54319e6f9fc3",
        "photo-1611517975989-c5882f8d2cf1",
        "photo-1571397872194-0ad8fbafe058",
        "photo-1704027689069-747471f0a40a",
        "photo-1756920681451-3103b5ca092d",
        "photo-1601987177651-8edfe6c20009",
        "photo-1590146758445-40be7019507d",
        "photo-1547638375-ebf04735d792",
        "photo-1642056446459-1f10774273f2",
        "photo-1589804845133-49b5e06cc415",
        "photo-1606167668584-78701c57f13d",
        "photo-1577896849786-738ed6c78bd3",
        "photo-1741321650126-32cbd6990f94",
        "photo-1651170104468-359c1a7fd53d",
        "photo-1681402720847-961bb1aab8d8",
        "photo-1611195974226-a6a9be9dd763",
        "photo-1526566661780-1a67ea3c863e",
        "photo-1586527155314-1d25428324ff",
        "photo-1684773585761-fde68b4ece42",
        "photo-1709399610754-921b7a9ef3b7",
        "photo-1605712916066-e143c317df72",
        "photo-1740119783893-e1d982de271c",
        "photo-1672267273720-053bee27b9a2",
        "photo-1644175897056-50f4d3a9a827",
        "photo-1646995477167-a344548ce6b9",
        "photo-1631106256072-54c89defe828",
        "photo-1633469924738-52101af51d87",
        "photo-1585366119957-e9730b6d0f60",
        "photo-1611604548018-d56bbd85d681",
        "photo-1638802538115-041e14d28d6a",
        "photo-1763986365305-109ad3ddbf2b",
        "photo-1651954393427-d4cf08360045",
        "photo-1726476391844-afeb2c887565",
        "photo-1638581777063-bf3ed0496c67",
        "photo-1602789216385-c6f910f9b450",
        "photo-1635048424329-a9bfb146d7aa",
        "photo-1608278047522-58806a6ac85b",
        "photo-1700909415800-6d2a5a83a234",
        "photo-1741512612523-d6b9b7cdd18b",
        "photo-1614082980086-62f20c181a57",
        "photo-1623040277749-1f241ff66a46",
        "photo-1771947010298-13b110b52954",
        "photo-1563209259-2819dbb22d93",
        "photo-1515488042361-ee00e0ddd4e4",
        "photo-1509676357509-2725362c42cb",
        "photo-1761644048584-4f7d8692eb79",
        "photo-1485783522162-1dbb8ffcbe5b",
        "photo-1779013494738-11c00e2354d1",
        "photo-1735893396744-966174c7580a",
    ],
    "Toys": [
        "photo-1596464716127-f2a82984de30",
        "photo-1519331379826-f10be5486c6f",
        "photo-1593085512500-5d55148d6f0d",
        "photo-1587654780291-39c9404d746b",
        "photo-1566577134770-3d85bb3a9cc4",
        "photo-1563941406054-949225931d52",
        "photo-1730804518415-75297e8d2a41",
        "photo-1629760946220-5693ee4c46ac",
        "photo-1612611741189-a9b9eb01d515",
        "photo-1588591795084-1770cb3be374",
        "photo-1494059980473-813e73ee784b",
        "photo-1611329857570-f02f340e7378",
        "photo-1677188010559-0667a1ed33a0",
        "photo-1612385763901-68857dd4c43c",
        "photo-1637120149073-54319e6f9fc3",
        "photo-1611517975989-c5882f8d2cf1",
        "photo-1571397872194-0ad8fbafe058",
        "photo-1704027689069-747471f0a40a",
        "photo-1756920681451-3103b5ca092d",
        "photo-1601987177651-8edfe6c20009",
        "photo-1590146758445-40be7019507d",
        "photo-1547638375-ebf04735d792",
        "photo-1642056446459-1f10774273f2",
        "photo-1589804845133-49b5e06cc415",
        "photo-1606167668584-78701c57f13d",
        "photo-1577896849786-738ed6c78bd3",
        "photo-1741321650126-32cbd6990f94",
        "photo-1651170104468-359c1a7fd53d",
        "photo-1681402720847-961bb1aab8d8",
        "photo-1611195974226-a6a9be9dd763",
        "photo-1526566661780-1a67ea3c863e",
        "photo-1586527155314-1d25428324ff",
        "photo-1684773585761-fde68b4ece42",
        "photo-1709399610754-921b7a9ef3b7",
        "photo-1605712916066-e143c317df72",
        "photo-1740119783893-e1d982de271c",
        "photo-1672267273720-053bee27b9a2",
        "photo-1644175897056-50f4d3a9a827",
        "photo-1646995477167-a344548ce6b9",
        "photo-1631106256072-54c89defe828",
        "photo-1633469924738-52101af51d87",
        "photo-1585366119957-e9730b6d0f60",
        "photo-1611604548018-d56bbd85d681",
        "photo-1638802538115-041e14d28d6a",
        "photo-1763986365305-109ad3ddbf2b",
        "photo-1651954393427-d4cf08360045",
        "photo-1726476391844-afeb2c887565",
        "photo-1638581777063-bf3ed0496c67",
        "photo-1602789216385-c6f910f9b450",
        "photo-1635048424329-a9bfb146d7aa",
        "photo-1608278047522-58806a6ac85b",
        "photo-1700909415800-6d2a5a83a234",
        "photo-1741512612523-d6b9b7cdd18b",
        "photo-1614082980086-62f20c181a57",
        "photo-1623040277749-1f241ff66a46",
        "photo-1771947010298-13b110b52954",
        "photo-1563209259-2819dbb22d93",
        "photo-1515488042361-ee00e0ddd4e4",
        "photo-1509676357509-2725362c42cb",
        "photo-1761644048584-4f7d8692eb79",
        "photo-1779013494738-11c00e2354d1",
        "photo-1735893396744-966174c7580a",
        "photo-1485783522162-1dbb8ffcbe5b",
    ],
    "Grocery & Gourmet": [
        "photo-1488459716781-31db52582fe9",
        "photo-1504674900247-0877df9cc836",
        "photo-1542838132-92c53300491e",
        "photo-1567620905732-2d1ec7ab7445",
        "photo-1540189549336-e6e99c3679fe",
        "photo-1471193945509-9ad0617afabf",
        "photo-1490645935967-10de6ba17061",
        "photo-1588964895597-cfccd6e2dbf9",
        "photo-1515706886582-54c73c5eaf41",
        "photo-1601600576337-c1d8a0d1373c",
        "photo-1685640206182-c51b8aa9b686",
        "photo-1543168256-418811576931",
        "photo-1628102491629-778571d893a3",
        "photo-1516594798947-e65505dbb29d",
        "photo-1557333610-90ee4a951ecf",
        "photo-1553531889-56cc480ac5cb",
        "photo-1550989460-0adf9ea622e2",
        "photo-1521566652839-697aa473761a",
        "photo-1614907634002-65ac4cb74acb",
        "photo-1565299624946-b28f40a0ae38",
        "photo-1555939594-58d7cb561ad1",
        "photo-1606787366850-de6330128bfc",
        "photo-1512621776951-a57141f2eefd",
        "photo-1467003909585-2f8a72700288",
        "photo-1476224203421-9ac39bcb3327",
        "photo-1482049016688-2d3e1b311543",
        "photo-1497034825429-c343d7c6a68f",
        "photo-1447933601403-0c6688de566e",
        "photo-1509042239860-f550ce710b93",
        "photo-1544787219-7f47ccb76574",
        "photo-1594631252845-29fc4cc8cde9",
        "photo-1558961363-fa8fdf82db35",
        "photo-1511381939415-e44015466834",
        "photo-1481391319762-47dff72954d9",
        "photo-1549007994-cb92caebd54b",
        "photo-1528735602780-2552fd46c7af",
        "photo-1499636136210-6f4ee915583e",
        "photo-1589927986089-35812388d1f4",
        "photo-1490474418585-ba9bad8fd0ea",
        "photo-1505253716362-afaea1d3d1af",
        "photo-1546069901-ba9599a7e63c",
        "photo-1512058564366-18510be2db19",
        "photo-1498837167922-ddd27525d352",
        "photo-1565958011703-44f9829ba187",
        "photo-1607083206968-13611e3d76db",
        "photo-1607082348824-0a96f2a4b9da",
        "photo-1533035353720-f1c6a75cd8ab",
        "photo-1495474472287-4d71bcdd2085",
        "photo-1596040033229-a9821ebd058d",
        "photo-1615485290382-441e4d049cb5",
        "photo-1547592180-85f173990554",
        "photo-1610970881699-44a5587cabec",
        "photo-1571115177098-24ec42ed204d",
        "photo-1615485925600-97237c4fc1ec",
    ],
    "Grocery": [
        "photo-1488459716781-31db52582fe9",
        "photo-1504674900247-0877df9cc836",
        "photo-1542838132-92c53300491e",
        "photo-1567620905732-2d1ec7ab7445",
        "photo-1540189549336-e6e99c3679fe",
        "photo-1471193945509-9ad0617afabf",
        "photo-1490645935967-10de6ba17061",
        "photo-1588964895597-cfccd6e2dbf9",
        "photo-1515706886582-54c73c5eaf41",
        "photo-1601600576337-c1d8a0d1373c",
        "photo-1685640206182-c51b8aa9b686",
        "photo-1543168256-418811576931",
        "photo-1628102491629-778571d893a3",
        "photo-1516594798947-e65505dbb29d",
        "photo-1557333610-90ee4a951ecf",
        "photo-1553531889-56cc480ac5cb",
        "photo-1550989460-0adf9ea622e2",
        "photo-1521566652839-697aa473761a",
        "photo-1614907634002-65ac4cb74acb",
    ],
    "Automotive": [
        "photo-1503376780353-7e6692767b70",
        "photo-1552519507-da3b142c6e3d",
        "photo-1544636331-e26879cd4d9b",
        "photo-1533473359331-0135ef1b58bf",
        "photo-1494976388531-d1058494cdd8",
        "photo-1583121274602-3e2820c69888",
        "photo-1708805282695-ef186db20192",
        "photo-1732357624591-f2137085659b",
        "photo-1694678505384-5c28eb08dc60",
        "photo-1632823469901-5d2cfff5ba50",
        "photo-1708805282683-50a060eba80f",
        "photo-1620584898989-d39f7f9ed1b7",
        "photo-1708805282706-f44730b7e527",
        "photo-1708805283017-c662be2c7a44",
        "photo-1694678505374-817757bcae89",
        "photo-1614888441158-de25f0ea4bc5",
        "photo-1565689876697-e467b6c54da2",
        "photo-1620584899131-a5ff5f8fbb03",
        "photo-1708805282676-0c15476eb8a2",
        "photo-1520340356584-f9917d1eea6f",
        "photo-1492144534655-ae79c964c9d7",
        "photo-1502877338535-766e1452684a",
        "photo-1549317661-bd32c8ce0db2",
        "photo-1553440569-bcc63803a83d",
        "photo-1506521781263-d8422e82f27a",
        "photo-1520031441872-265e4ff70366",
        "photo-1449965408869-eaa3f722e40d",
        "photo-1580273916550-e323be2ae537",
        "photo-1502161254066-6c74afbf07aa",
        "photo-1542362567-b07e54358753",
        "photo-1560958089-b8a1929cea89",
        "photo-1549399542-7e3f8b79c341",
        "photo-1511919884226-fd3cad34687c",
        "photo-1503631285924-e1544dce8b28",
        "photo-1546039907-7fa05f864c02",
        "photo-1552930294-6b595f4c2974",
        "photo-1517524008697-84bbe3c3fd98",
        "photo-1558618666-fcd25c85cd64",
        "photo-1517672651691-24622a91b550",
        "photo-1542282088-fe8426682b8f",
        "photo-1568605117036-5fe5e7bab0b7",
        "photo-1585704032915-c3400ca199e7",
        "photo-1605559424843-9e4c228bf1c2",
        "photo-1606016159991-dfe4f2746ad5",
        "photo-1583267746897-2cf415887172",
        "photo-1494905998402-395d579af36f",
        "photo-1489824904134-891ab64532f1",
        "photo-1493238792000-8113da705763",
        "photo-1533106418989-88406c7cc8ca",
        "photo-1516714435131-44d6b64dc6a2",
        "photo-1571068316344-75bc76f77890",
        "photo-1580274455191-1c62238fa333",
        "photo-1555215695-3004980ad54e",
        "photo-1551721434-8b94ddff0e6d",
        "photo-1558981806-ec527fa84c39",
        "photo-1519641471654-76ce0107ad1b",
        "photo-1544829099-b9a0c07fad1a",
        "photo-1551524559-8af4e6624178",
        "photo-1550355291-bbee04a92027",
        "photo-1567818735868-e71b99932e29",
        "photo-1592853625601-bb9d23da12fc",
    ],
    "Pet Supplies": [
        "photo-1544568100-847a948585b9",
        "photo-1568572933382-74d440642117",
        "photo-1583511655857-d19b40a7a54e",
        "photo-1516734212186-a967f81ad0d7",
    ],
    "Office & Stationery": [
        "photo-1497366754035-f200968a6e72",
        "photo-1497366216548-37526070297c",
        "photo-1517842645767-c639042777db",
        "photo-1497366811353-6870744d04b2",
        "photo-1503958014551-3b41f69234d9",
        "photo-1606327054536-e37e655d4f4a",
        "photo-1474377207190-a7d8b3334068",
        "photo-1501959181532-7d2a3c064642",
        "photo-1508873699372-7aeab60b44ab",
        "photo-1513077202514-c511b41bd4c7",
        "photo-1531347334762-59780ece5c76",
        "photo-1507831228884-93d43e81a99d",
        "photo-1531256379416-9f000e90aacc",
        "photo-1510070009289-b5bc34383727",
        "photo-1531347118459-c3ea7a5ac61e",
        "photo-1513127971914-6a8656fc9718",
        "photo-1761322572550-967ea8c0bfd9",
        "photo-1620275765334-4ed948bb4502",
        "photo-1501618669935-18b6ecb13d6d",
        "photo-1531346878377-a5be20888e57",
        "photo-1581431886211-6b932f8367f2",
        "photo-1623697899811-f2403f50685e",
        "photo-1507737487170-feae809cb2ab",
        "photo-1758521232691-613561977b6a",
        "photo-1759746571141-30a56dde257e",
        "photo-1777915515462-0a22a26ac430",
        "photo-1501349800519-48093d60bde0",
        "photo-1513542789411-b6a5d4f31634",
        "photo-1612815154858-60aa4c59eaa6",
        "photo-1559209537-dafe2fe2886b",
        "photo-1625465104350-6db75b747a1d",
        "photo-1602867005582-997b8dbf0813",
        "photo-1706895040634-62055892cbbb",
        "photo-1715059448930-9dff21725605",
        "photo-1650094980833-7373de26feb6",
        "photo-1625961332771-3f40b0e2bdcf",
        "photo-1688578735427-994ecdea3ea4",
        "photo-1688578735352-9a6f2ac3b70a",
        "photo-1571624436279-b272aff752b5",
        "photo-1641794008048-d863bb4a23d3",
        "photo-1669985457873-0c540a1d832a",
        "photo-1594235048794-fae8583a5af5",
        "photo-1595846723416-99a641e1231a",
        "photo-1688578735122-f37256f1b8b0",
        "photo-1518455027359-f3f8164ba6bd",
        "photo-1734605052354-62d450e0e5ff",
        "photo-1734605044291-d0a3d1bf3588",
        "photo-1689691811704-ae78d70117ce",
        "photo-1689691849957-1ce9f9315e91",
        "photo-1498050108023-c5249f4df085",
        "photo-1593642702821-c8da6771f0c6",
        "photo-1492138786289-d35ea832da43",
        "photo-1510519138101-570d1dca3d66",
        "photo-1616440347437-b1c73416efc2",
        "photo-1669723027015-9a3cfab8c5df",
        "photo-1468779036391-52341f60b55d",
        "photo-1569235186275-626cb53b83ce",
        "photo-1583521214690-73421a1829a9",
        "photo-1768158989131-64cbff67f292",
        "photo-1750935578389-6e1445f5fd8d",
        "photo-1649954174454-767fd0a40fb6",
        "photo-1629652487043-fb2825838f8c",
        "photo-1718306155883-3f0bc8fbf881",
        "photo-1725801731069-baa524d6bd4c",
        "photo-1577733975197-3b950ca5cabe",
        "photo-1755040334245-a38461eaddf7",
        "photo-1758630737361-ca7532fb5e7f",
    ],
    "Baby & Kids": [
        "photo-1515488042361-ee00e0ddd4e4",
        "photo-1519689680058-324335c77eba",
        "photo-1544717305-2782549b5136",
        "photo-1559454403-b8fb88521f11",
        "photo-1543346242-2b8e41fb91ca",
        "photo-1501686637-b7aa9c48a882",
        "photo-1484820540004-14229fe36ca4",
        "photo-1589827711524-0fb39b96e630",
        "photo-1545558014-8692077e9b5c",
        "photo-1549501602-52168bb8f653",
        "photo-1685358268305-c621b38e75d8",
        "photo-1560859251-d563a49c5e4a",
        "photo-1618842676088-c4d48a6a7c9d",
        "photo-1622290319146-7b63df48a635",
        "photo-1505043203398-7e4c111acbfa",
        "photo-1504484656217-38f8ffc617f9",
        "photo-1516627145497-ae6968895b74",
        "photo-1503454537195-1dcabb73ffb9",
        "photo-1531835551805-16d864c8d311",
        "photo-1536304929831-ee1ca9d44906",
        "photo-1503919545889-aef636e10ad4",
        "photo-1555252333-9f8e92e65df9",
        "photo-1574158622682-e40e69881006",
        "photo-1542596768-5d1d21f1cf98",
        "photo-1476703993599-0035a21b17a9",
        "photo-1583337130417-3346a1be7dee",
        "photo-1531824475211-72594993ce2a",
        "photo-1555854877-bab0e564b8d5",
        "photo-1553456558-aff63285bdd1",
        "photo-1590959651373-a3db0f38a961",
        "photo-1606131731446-5568d87113aa",
        "photo-1609521263047-f8f205293f24",
    ],
    "Health & Wellness": [
        "photo-1740479050129-7fef21254518",
        "photo-1548966268-b978ed7b2e83",
        "photo-1579126038374-6064e9370f0f",
        "photo-1556911073-a517e752729c",
        "photo-1635367216109-aa3353c0c22e",
        "photo-1579722820308-d74e571900a9",
        "photo-1666979289472-96e6d3245b84",
        "photo-1528272252360-5efd274e36fb",
        "photo-1670850757896-e1b6c3e311ea",
    ],
    "Music & Media": [
        "photo-1511379938547-c1f69419868d",
        "photo-1493225457124-a3eb161ffa5f",
        "photo-1514320291840-2e0a9bf2a9ae",
        "photo-1504898770365-14faca6a7320",
        "photo-1672073314527-cd2d83182992",
        "photo-1619468654328-5fefe028d42b",
        "photo-1585838017777-5003198884b5",
        "photo-1673427079629-418917214ffc",
        "photo-1550134464-4c07c5b02073",
        "photo-1543840950-e6529649ce74",
        "photo-1619983081563-430f63602796",
        "photo-1580656449278-e8381933522c",
        "photo-1643698512439-4485caa5a7d1",
        "photo-1669801158950-f663cf15298c",
        "photo-1588532218970-c2cab983746a",
        "photo-1535833438489-c1774eaa5225",
        "photo-1470225620780-dba8ba36b745",
        "photo-1458560871784-56d23406c091",
        "photo-1525201548942-d8732f6617a0",
        "photo-1461141346587-763ab02bced9",
        "photo-1516280440614-37939bbacd81",
        "photo-1487180144351-b8472da7d491",
        "photo-1519638399535-1b036603ac77",
        "photo-1598488035139-bdbb2231ce04",
        "photo-1510915361894-db8b60106cb1",
        "photo-1598653222000-6b7b7a552625",
        "photo-1587731556938-38755b4803a6",
        "photo-1516450360452-9312f5e86fc7",
        "photo-1459749411175-04bf5292ceea",
        "photo-1470229722913-7c0e2dbbafd3",
        "photo-1520523839897-bd0b52f945a0",
        "photo-1598554747436-c9293d6a588f",
        "photo-1593642702821-c8da6771f0c6",
        "photo-1507525428034-b723cf961d3e",
        "photo-1516035069371-29a1b244cc32",
        "photo-1533174072545-7a4b6ad7a6c3",
        "photo-1465847899084-d164df4dedc6",
        "photo-1558862107-d49ef2a04d72",
    ],
}


def random_name() -> tuple[str, str]:
    """Generate a realistic full name."""
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    return first, last


def generate_email(first: str, last: str, idx: int) -> str:
    """Generate a realistic email address with index suffix for uniqueness."""
    domains = ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "protonmail.com", "icloud.com", "aol.com"]
    patterns = [
        f"{first.lower()}.{last.lower()}",
        f"{first.lower()}{last.lower()}",
        f"{first[0].lower()}{last.lower()}",
        f"{first.lower()}_{last.lower()}",
        f"{last.lower()}{first[0].lower()}",
    ]
    local = random.choice(patterns)
    # Append index to guarantee uniqueness
    return f"{local}{idx}@{random.choice(domains)}"


def _pet_image_pool(name: str, subcategory: str) -> list[str]:
    """Pick a species-appropriate image pool for Pet Supplies products."""
    text = f"{subcategory} {name}".lower()
    cat_keywords = ["cat", "kitten", "catnip", "kitty"]
    dog_keywords = ["dog", "puppy", "canine"]
    has_cat = any(k in text for k in cat_keywords)
    has_dog = any(k in text for k in dog_keywords)
    if has_cat:
        return list(PET_CAT_IMAGE_POOL)
    if has_dog:
        return list(PET_DOG_IMAGE_POOL)
    # Mixed or neutral products (grooming gloves, nail grinders, etc.)
    return PET_CAT_IMAGE_POOL + PET_DOG_IMAGE_POOL


# Shared "already assigned" tracker per image pool (keyed by category or
# category::subcategory) so that within one seeding/migration run every product
# gets a unique photo from its pool wherever the pool is large enough.
_assigned_image_ids: dict[str, set[str]] = {}


def _pick_pool_image(product_id: str, pool_key: str, pool: list[str]) -> str:
    """Pick a photo unique within this run for the given pool key.

    Starts from the product's hash slot then linear-probes the pool for the
    first image not already assigned to another product that draws from the
    same pool. Falls back to the hash slot if the whole pool is exhausted so
    re-seeding can never deadlock.
    """
    start = int(hashlib.sha256(product_id.encode()).hexdigest(), 16) % len(pool)
    used = _assigned_image_ids.setdefault(pool_key, set())
    idx = start
    for _ in range(len(pool)):
        if pool[idx] not in used:
            used.add(pool[idx])
            return f"https://images.unsplash.com/{pool[idx]}?w=400&h=300&fit=crop"
        idx = (idx + 1) % len(pool)
    return f"https://images.unsplash.com/{pool[start]}?w=400&h=300&fit=crop"


def get_product_image_url(product_id: str, category: str, subcategory: str = "", name: str = "") -> str:
    """Return a category-relevant image URL using a stable pool of Unsplash photos.
    Uses a deterministic hash of the product_id so the same product always gets
    the same image from its category's image pool.
    When a subcategory-specific pool exists (e.g. Electronics subcategories),
    images are drawn from that pool for better visual relevance.
    Every product gets a unique image within its pool during a seeding/migration
    run (collision-free assignment). Pet Supplies products are drawn from
    species-specific pools so cat and dog products never mix photos."""
    if category == "Pet Supplies":
        return _pick_pool_image(product_id, "Pet Supplies", _pet_image_pool(name, subcategory))
    pool = CATEGORY_IMAGE_POOL.get(category, CATEGORY_IMAGE_POOL.get("Electronics", []))
    pool_key = category
    if subcategory and subcategory in SUBCATEGORY_IMAGE_POOL:
        pool = SUBCATEGORY_IMAGE_POOL[subcategory]
        pool_key = f"{category}::{subcategory}"
    return _pick_pool_image(product_id, pool_key, pool)


def generate_product(product_id: str, category: str, subcategory: str, brand: str, name_suffix: str, price: float) -> dict:
    """Generate a product dict from explicit definition."""
    product_name = f"{brand} {name_suffix}"
    # Generate a deterministic-but-realistic rating (3.5–5.0)
    hash_val = int(hashlib.sha256(product_id.encode()).hexdigest(), 16)
    rating = 3.5 + (hash_val % 15) / 10
    rating = min(5.0, round(rating, 1))
    # ~40% of products have a discount
    has_discount = (hash_val % 5) != 0 and (hash_val % 3) != 0
    discount_percent = None
    original_price = None
    if has_discount:
        discount_percent = 5 + (hash_val % 26)
        original_price = round(price / (1 - discount_percent / 100), 2)
    return {
        "product_id": product_id,
        "name": product_name,
        "category": category,
        "subcategory": subcategory,
        "brand": brand,
        "price": price,
        "rating": rating,
        "discount_percent": discount_percent,
        "original_price": original_price,
        "image_url": get_product_image_url(product_id, category, subcategory, product_name),
    }


def generate_event_time(base_date: datetime, day_offset: int) -> datetime:
    """Generate a realistic event timestamp with hour-of-day bias."""
    # Business hours: 8am-11pm, peak at 10am-2pm and 6pm-9pm
    hour_weights = [0] * 24
    for h in range(8, 23):
        if 10 <= h <= 14:
            hour_weights[h] = 15
        elif 18 <= h <= 21:
            hour_weights[h] = 12
        else:
            hour_weights[h] = 5

    # Weekend vs weekday: slightly more activity on weekends
    event_date = base_date + timedelta(days=day_offset)

    hour = random.choices(range(24), weights=hour_weights, k=1)[0]
    minute = random.randint(0, 59)
    second = random.randint(0, 59)

    return event_date.replace(hour=hour, minute=minute, second=second, microsecond=0)


def get_segments_for_customer(metrics: dict) -> list[str]:
    """Determine which segments a customer belongs to based on their metrics."""
    assigned = []
    if metrics.get("lifetime_value", 0) > 500 and metrics.get("purchases", 0) > 5:
        assigned.append("high_value")
    if metrics.get("avg_price", 999) < 30 and metrics.get("purchases", 0) > 3:
        assigned.append("bargain_hunter")
    if metrics.get("days_since_first", 999) < 30:
        assigned.append("new_user")
    if metrics.get("days_since_last", 0) > 90:
        assigned.append("lapsed")
    if metrics.get("cart_events", 0) > metrics.get("purchases", 0) and metrics.get("cart_events", 0) > 2:
        assigned.append("cart_abandoner")
    if metrics.get("top_brand_pct", 0) > 0.5 and metrics.get("purchases", 0) > 3:
        assigned.append("brand_loyalist")
    if metrics.get("views", 0) > 50 and metrics.get("purchases", 0) == 0:
        assigned.append("window_shopper")
    if metrics.get("events_30d", 0) > 100:
        assigned.append("power_user")
    return assigned


def generate_price_tier(price: float) -> str:
    if price < 30:
        return "budget"
    elif price < 80:
        return "mid"
    elif price < 150:
        return "premium"
    else:
        return "luxury"


# ── Main Seed Function ──────────────────────────────────────────────────────

async def seed_database(db: AsyncSession) -> None:
    """
    Seed the database with synthetic data if it's empty.
    Creates products, customers, events, segments, and offers.
    """
    # Check if data already exists
    result = await db.execute(select(func.count(Event.event_id)))
    count = result.scalar()
    if count and count > 0:
        logger.info(f"Database already has {count} events. Skipping seed.")
        return

    logger.info("Seeding database with synthetic data...")
    base_date = utcnow() - timedelta(days=90)
    now = utcnow()

    # ── Generate Products ──
    products = []
    for category, subcategories in PRODUCT_DEFINITIONS.items():
        for subcategory, product_list in subcategories.items():
            for brand, name_suffix, price in product_list:
                product_id = str(uuid.uuid4())
                product_data = generate_product(product_id, category, subcategory, brand, name_suffix, price)
                products.append(product_data)

    # Insert products
    product_objects = {}
    for p in products:
        obj = Product(**p)
        db.add(obj)
        product_objects[p["product_id"]] = obj

    # Flush to get IDs
    await db.flush()

    logger.info(f"Generated {len(products)} products.")

    # ── Generate Customers ──
    customers = []
    customer_count = settings.CUSTOMER_COUNT

    # Seed explicit Admin User
    admin_customer = Customer(
        customer_id=str(uuid.uuid4()),
        name="Admin User",
        email="admin@personalshop.com",
        consent_given=True,
        consent_timestamp=now,
        created_at=base_date,
        role="admin",
        password_hash=hash_password(settings.DEMO_PASSWORD, rounds=10),
    )
    db.add(admin_customer)
    customers.append(admin_customer)

    for i in range(customer_count):
        customer_id = str(uuid.uuid4())
        first, last = random_name()
        name = f"{first} {last}"
        email = generate_email(first, last, i)
        # 50% consent rate
        consent_given = random.random() < 0.5

        customer = Customer(
            customer_id=customer_id,
            name=name,
            email=email,
            consent_given=consent_given,
            consent_timestamp=now if consent_given else None,
            created_at=base_date + timedelta(days=random.randint(0, 60)),
            password_hash=hash_password(settings.DEMO_PASSWORD, rounds=10),
        )
        db.add(customer)
        customers.append(customer)

    await db.flush()
    logger.info(f"Generated {customer_count} customers.")

    # ── Generate Events ──
    event_count = settings.EVENT_COUNT
    events_data = []

    # Assign activity levels (pareto-style: 20% of customers generate 80% of events)
    activity_weights = []
    for _ in range(len(customers)):
        # Some customers are power users, most are casual
        base_weight = random.expovariate(0.5) + 0.1
        activity_weights.append(base_weight)

    total_weight = sum(activity_weights)
    event_assignments = [max(1, int(event_count * w / total_weight)) for w in activity_weights]

    # Adjust to exactly match event_count
    diff = event_count - sum(event_assignments)
    assign_len = len(event_assignments)
    for i in range(abs(diff)):
        event_assignments[i % assign_len] += 1 if diff > 0 else -1

    customer_product_affinities = {}  # customer_id -> list of product_id (preferred products)
    customer_purchase_history = {}  # customer_id -> list of product_id (purchased products)

    for cust_idx, customer in enumerate(customers):
        customer_id = customer.customer_id
        # Privacy guardrail: do not generate behavioural events for customers
        # who have not given consent for personalisation.
        if not customer.consent_given:
            continue
        num_events = event_assignments[cust_idx]

        # Pick a preferred category for this customer
        preferred_categories = random.choices(list(CATEGORIES.keys()), k=random.randint(1, 3))
        # Get products in preferred categories
        preferred_products = [p for p in products if p["category"] in preferred_categories]

        purchased_products = []
        viewed_products = set()

        for _ev_idx in range(num_events):
            # Determine event type based on weights
            event_type = random.choices(
                list(EVENT_WEIGHTS.keys()),
                weights=list(EVENT_WEIGHTS.values()),
                k=1
            )[0]

            # Pick a product (biased toward preferred categories)
            if preferred_products and random.random() < 0.7:
                product = random.choice(preferred_products)
            else:
                product = random.choice(products)

            product_id = product["product_id"]

            # Day offset: skewed toward recent days with some spread across 90 days
            if event_type == "purchase":
                # Purchases more recent
                day_offset = random.randint(0, 60)
            else:
                day_offset = random.randint(0, 89)

            event_time = generate_event_time(base_date, day_offset)

            metadata = None
            if event_type == "page_view":
                metadata = {"scroll_depth": random.randint(10, 100), "time_on_page": random.randint(5, 300)}
                viewed_products.add(product_id)
            elif event_type == "purchase":
                metadata = {"quantity": random.randint(1, 5), "total_price": product["price"] * random.randint(1, 5)}
                purchased_products.append(product_id)
            elif event_type in ("add_to_cart", "remove_from_cart"):
                metadata = {"quantity": random.randint(1, 3)}
            elif event_type in ("email_open", "email_click"):
                metadata = {"campaign": random.choice(["newsletter", "promo", "abandoned_cart", "welcome"])}
            elif event_type == "wishlist_add":
                metadata = {"note": random.choice(["", "gift idea", "birthday wishlist"])}

            events_data.append({
                "event_id": str(uuid.uuid4()),
                "customer_id": customer_id,
                "product_id": product_id,
                "event_type": event_type,
                "session_id": str(uuid.uuid4()) if random.random() < 0.3 else None,
                "metadata": metadata,
                "event_timestamp": event_time,
            })

        customer_product_affinities[customer_id] = list(viewed_products)
        customer_purchase_history[customer_id] = purchased_products

    # Insert events in batches
    batch_size = 500
    for i in range(0, len(events_data), batch_size):
        batch = events_data[i:i+batch_size]
        for ev_data in batch:
            event = Event(**ev_data)
            db.add(event)
        await db.flush()

    logger.info(f"Generated {len(events_data)} events.")

    # ── Compute metrics and assign segments ──
    from app.offers import OfferEngine
    offer_engine = OfferEngine(db)

    segment_assignments = 0
    for customer in customers:
        metrics = await offer_engine._compute_metrics(customer.customer_id)

        # Add derived metrics for segment evaluation
        metrics["purchases"] = len(customer_purchase_history.get(customer.customer_id, []))
        metrics["views"] = len(customer_product_affinities.get(customer.customer_id, []))

        # Calculate top brand percentage
        purchase_pids = customer_purchase_history.get(customer.customer_id, [])
        if purchase_pids:
            brand_counts = {}
            for pid in purchase_pids:
                p = next((pr for pr in products if pr["product_id"] == pid), None)
                if p and p.get("brand"):
                    brand_counts[p["brand"]] = brand_counts.get(p["brand"], 0) + 1
            if brand_counts:
                metrics["top_brand_pct"] = max(brand_counts.values()) / len(purchase_pids)

        segments = get_segments_for_customer(metrics)
        now = utcnow()
        for segment in segments:
            db.add(CustomerSegment(
                customer_id=customer.customer_id,
                segment=segment,
                assigned_at=now,
            ))
            segment_assignments += 1

    logger.info(f"Assigned {segment_assignments} segments across customers.")

    # ── Seed offers ──
    await offer_engine.seed_offers()
    await offer_engine.assign_offers()

    logger.info("Database seeding complete!")


async def ensure_demo_passwords(db: AsyncSession) -> None:
    """Backfill a documented default password for seeded/demo accounts.

    Accounts created before password support (the seeded 500 customers and the
    seeded admin) have a NULL password_hash. To keep the demo usable we assign
    them the shared demo password. Real accounts created via signup always have
    their own password and are unaffected.
    """
    demo_hash = hash_password(settings.DEMO_PASSWORD, rounds=10)
    result = await db.execute(
        select(Customer).where(Customer.password_hash.is_(None))
    )
    pending = result.scalars().all()
    for c in pending:
        c.password_hash = demo_hash
    if pending:
        logger.info("Backfilled demo password for %s legacy/seed customer(s).", len(pending))
