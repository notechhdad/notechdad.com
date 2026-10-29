"""Build notechdad.com straight into this repository.

Usage, from anywhere:
  python3 _src/build.py                 rebuild the HTML pages, 404.html, sitemap.xml and CNAME in the repo root
  python3 _src/build.py --preview DIR   also write a preview copy (Google Fonts, images copied) into DIR

Sources, all in _src/:
  web/style.css, web/extra.css   design tokens and components
  web/pages/                     hand-written page parts (home, about, method, news)
  web/results/                   one lab plate per published result
  data/videos.json               public data for the long-form videos (title, date, length, views)
  this file                      dates, inventory, useful links, results, video blurbs and video pages
Images (img/), icons, the share image, fonts/ and robots.txt are committed in the repo root and are not
regenerated. The build ends with checks: broken internal links, and anything private that must never
be published. See _src/README.md for the refresh procedure.
"""
import argparse, html, json, re, shutil, sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

SRC = Path(__file__).resolve().parent
REPO = SRC.parent
W = SRC / "web"
ARGS = argparse.ArgumentParser(description="Build notechdad.com into the repo root.")
ARGS.add_argument("--preview", metavar="DIR", help="also write a preview copy of the site into DIR")
ARGS = ARGS.parse_args()
DOMAIN = "https://notechdad.com/"

def show(iso):
    d = datetime.strptime(iso, "%Y-%m-%d")
    return f"{d.day} {d:%b %Y}"

# ISO dates. Change one when that part of the site is re-checked; the site shows them as "14 Oct 2026".
DATES = {
    "updated": "2026-10-29",     # footer stamp, results page, sitemap
    "inventory": "2026-10-14",   # bench page
    "links": "2026-10-22",       # useful links and the latest drivers
    "news": "2026-10-29",        # news page and the home page's news column
}
UPDATED, SITEMAP_DATE = show(DATES["updated"]), DATES["updated"]
INV_DATE, LINKS_DATE, NEWS_DATE = show(DATES["inventory"]), show(DATES["links"]), show(DATES["news"])
EMAIL = "Nizzel@notechdad.com"
CHANNEL = "https://www.youtube.com/@no_tech-dad"
SUBSCRIBE = CHANNEL + "?sub_confirmation=1"
# Visitor counting with GoatCounter (cookie-free). Set to the site code from goatcounter.com, e.g. "notechdad".
# Empty means no counter is added to the pages.
GOATCOUNTER = "notechdad"
def counter_tag():
    if not GOATCOUNTER:
        return ""
    return (f'<script data-goatcounter="https://{GOATCOUNTER}.goatcounter.com/count" async '
            'src="//gc.zgo.at/count.js"></script>\n'
            '<script>document.addEventListener("click",function(e){var a=e.target.closest&&e.target.closest("a[href*=\'youtube.com\']");'
            'if(!a||!window.goatcounter||!window.goatcounter.count)return;var h=a.getAttribute("href"),'
            'n=h.indexOf("sub_confirmation")>-1?"subscribe":(h.match(/v=([\\w-]+)/)?"watch-"+h.match(/v=([\\w-]+)/)[1]:"channel");'
            'window.goatcounter.count({path:"click-"+n,title:a.textContent.trim().slice(0,60),event:true})});</script>\n')
CSS = (W / "style.css").read_text() + "\n" + (W / "extra.css").read_text()
GF = ('<link rel="preconnect" href="https://fonts.googleapis.com">\n'
      '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
      '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Big+Shoulders+Display:wght@700;800;900'
      '&family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap">')
e = html.escape

def part(name):
    return (W / "pages" / name).read_text()

# ================================================================ inventory
# (asset id, device, chip, vendor, architecture, note)
HANDHELDS = [
    ("H01", "Steam Deck OLED", "Custom APU (Sephiroth)", "AMD", "Van Gogh", "White edition · SteamOS"),
    ("H03", "ROG Xbox Ally", "Ryzen Z2 A", "AMD", "Van Gogh", ""),
    ("H07", "Legion Go S", "Ryzen Z1 Extreme", "AMD", "Phoenix", "SteamOS · 32 GB"),
    ("H02", "ROG Xbox Ally X", "Ryzen AI Z2 Extreme", "AMD", "Strix Point", ""),
    ("H05", "MSI Claw A8", "Ryzen Z2 Extreme", "AMD", "Strix Point", "No NPU"),
    ("H09", "OneXPlayer X1 Pro", "Ryzen AI 9 HX 470", "AMD", "Gorgon Point", ""),
    ("H13", "OneXFly Apex", "Ryzen AI Max+ 395", "AMD", "Strix Halo", "96 GB"),
    ("H15", "AYANEO Next 2", "Ryzen AI Max+ 395", "AMD", "Strix Halo", ""),
    ("H12", "OneXPlayer X2 Mini Pro", "Ryzen AI Max+", "AMD", "Strix Halo", "Orange · 2 TB"),
    ("H26", "GPD Win Max 3", "Ryzen AI Max+ 395", "AMD", "Strix Halo", "128 GB"),
    ("H27", "GPD Win 5", "Ryzen AI Max+ 388", "AMD", "Strix Halo", "32 GB"),
    ("H04", "MSI Claw A1M", "Core Ultra 7 155H", "Intel", "Meteor Lake", ""),
    ("H06", "MSI Claw 8 AI+", "Core Ultra 7 258V", "Intel", "Lunar Lake", ""),
    ("H10", "OneXPlayer X2", "Arc G3 Extreme", "Intel", "Panther Lake", ""),
    ("H11", "OneXPlayer 3", "Arc G3 Extreme", "Intel", "Panther Lake", ""),
    ("H14", "OneXFly Apex Air", "Arc G3 Extreme", "Intel", "Panther Lake", ""),
    ("H25", "MSI Claw 8 EX AI+", "Arc G3 Extreme", "Intel", "Panther Lake", ""),
]
ARCH = {
    "AMD": [("Van Gogh", "and Van Gogh class"), ("Phoenix", "Zen 4, RDNA 3"), ("Strix Point", "Zen 5, RDNA 3.5"),
            ("Gorgon Point", "a Strix Point refresh"), ("Strix Halo", "Ryzen AI Max+")],
    "Intel": [("Meteor Lake", "Core Ultra series 1"), ("Lunar Lake", "Core Ultra series 2"),
              ("Panther Lake", "Intel Arc G-series")],
}
# (id, title, lead, groups); groups = [(group label or None, [(asset id, device, details, note)])]
SECTIONS = [
    ("android", "Android handhelds", "", [(None, [
        ("H17", "AYANEO Pocket AIR Mini", "", ""), ("H21", "AYANEO KONKR Pocket BLOCK", "", ""),
        ("H18", "AYN Thor", "", ""), ("H19", "AYN Odin 3", "", "")])]),
    ("consoles", "Consoles", "", [
        ("Sony", [("C08", "PlayStation 5 Pro", "", ""),
                  ("C09", "PlayStation 4 Pro", "500 Million Limited Edition", ""), ("H32", "PlayStation Vita", "", ""),
                  ("H33", "PlayStation Portable (PSP)", "", "")]),
        ("Nintendo", [("H29", "Nintendo Switch 2", "", ""), ("H30", "Nintendo Switch", "", ""),
                      ("H31", "Nintendo Switch Lite", "", "")])]),
    ("mini-pcs", "Mini PCs", "", [(None, [
        ("C01", "Minisforum AI X1 Pro", "Ryzen AI 9 HX 470", "OCuLink"),
        ("C03", "Beelink GTi15 Ultra", "", "")])]),
    ("desktop", "Desktop test bench", "", [(None, [
        ("C06", "ASUS ROG Crosshair X870E Hero", "Motherboard", ""),
        ("C07", "Open-air test bench", "Frame", "")])]),
    ("gpus", "Graphics cards", "", [(None, [
        ("G01", "ASUS ROG Astral RTX 5090", "", ""), ("G03", "NVIDIA RTX 5090 Founders Edition", "", ""),
        ("G06", "NVIDIA RTX 4090 Founders Edition", "", ""), ("G07", "RTX 5070", "", ""),
        ("G04", "RTX 4070 Super", "", ""), ("G12", "RTX 5060 Ti", "", ""), ("G05", "RTX 4060", "", ""),
        ("G08", "RTX 5050", "", "")])]),
    ("egpus", "External GPUs", "", [(None, [
        ("G09", "ASUS ROG XG Mobile", "RTX 5090", ""), ("G10", "MOREFINE 5090M", "", ""),
        ("G11", "AORUS RTX 5060 Ti eGPU", "", "")])]),
    ("docks", "Docks", "", [
        ("eGPU docks", [("D01", "Minisforum DEG2", "", ""), ("D02", "AOOSTAR AG03", "OCuLink", ""),
                        ("D03", "UGREEN Link Station", "", "")]),
        ("Expansion docks", [("D04", "Beelink EX dock", "", ""), ("D05", "Beelink EX Mate Pro", "", "")]),
        ("Thunderbolt and USB-C docks", [("D09", "Razer Thunderbolt Dock Chroma", "", ""),
                                         ("D06", "JSAUX 5-in-1 dock", "", ""), ("D07", "UGREEN 6-in-1 dock", "", ""),
                                         ("D08", "Anker 14-in-1 dock", "", "")])]),
    ("displays", "Displays", "", [(None, [
        ("M01", "ASUS ROG Strix XG32UCWMG", "32-inch", ""), ("M02", "ASUS ROG Swift PG27UCDM", "27-inch", "Used in portrait"),
        ("M06", "UPERFECT portable monitor", "16-inch", ""), ("M07", "Aura dual-screen display", "16-inch", ""),
        ("M03", "Arzopa portable monitor", "", ""), ("M04", "Minisforum dual-screen portable monitor", "", ""),
        ("M05", "Wiseco AMOLED USB-C screen", "7-inch", "Second screen")])]),
    ("power", "Power and measurement", "", [(None, [
        ("P04", "TP-Link Tapo P110M ×2", "Smart plug with energy monitoring", "Wall power for each setup"),
        ("P01", "Anker Prime charger", "160W", ""), ("P02", "CUKTECH 30 Ultra charger", "300W", ""),
        ("P03", "OneXPlayer Frost Bay", "Cooling dock", "")])]),
    ("filming", "Filming", "", [(None, [
        ("F01", "Sony FX30", "Main camera", ""), ("F02", "Sony ZV-E10 II", "Second camera", ""),
        ("F07", "iPhone 17 Pro", "Camera and teleprompter", ""), ("F06", "Insta360 Luna Ultra", "Gimbal camera", ""),
        ("F03", "Insta360 GO 3S", "POV camera", ""), ("F04", "Insta360 Link 2C Pro", "Webcam", ""),
        ("F09", "Hollyland Lark M2", "Wireless mics", ""), ("F10", "BOYA wireless mic", "Wireless mic", ""),
        ("F11", "Elgato Key Light ×3", "Lighting", ""),
        ("F13", "Blackmagic DeckLink Quad HDMI Recorder", "Capture card", "")])]),
]
SOFTWARE = "DaVinci Resolve · OBS Studio · CapFrameX · HWiNFO64 · RTSS · Blackmagic Camera"
INCOMING = [  # asset, device, details, status, chip class
    ("H20", "ROG Xbox Ally X20", "20th-anniversary bundle", "Ordered", "t-info"),
    ("H28", "Acer Predator Atlas 8", "Intel Arc G3", "Back-ordered", "t-info"),
    ("C05", "Valve Steam Machine", "", "Bought", "t-info"),
    ("C04", "Piston V", "Ryzen AI 9 HX 370 · 64 GB · 4 TB", "Backed · est. Jan 2027", "t-mute"),
    ("C10", "GPD BOX", "Core Ultra 7 356H · 32 GB · 1 TB", "Backed", "t-mute"),
    ("D12", "GPD G2 eGPU dock", "MCIO 8i and USB4 v2 · bundled with the GPD BOX", "Backed", "t-mute"),
]

def count(groups):
    return sum(len(rows) for _, rows in groups)

ON_BENCH = len(HANDHELDS) + sum(count(g) for *_, g in SECTIONS)

# ================================================================ useful links (checked on LINKS_DATE)
# (vendor line, product, version, status tag or None, release date, note, [(link label, url)])
DRIVERS = [
    ("AMD · Radeon graphics", "Adrenalin Edition", "26.10.1", "Recommended", "20 Oct 2026",
     "Adds support for Call of Duty: Modern Warfare 4 and brings FSR Upscaling 4.1 to Radeon RX 6000 cards and "
     "Ryzen AI chips. AMD's notes say this package doesn't support handheld PCs, so get handheld drivers from the maker.",
     [("Release notes", "https://www.amd.com/en/resources/support-articles/release-notes/RN-RAD-WIN-26-10-1.html"),
      ("Download page", "https://www.amd.com/en/support/download/drivers.html")]),
    ("Intel · Arc graphics", "Arc and Core Ultra graphics", "101.9150", "WHQL", "12 Oct 2026",
     "Full version 32.0.101.9150. It covers Arc A- and B-series cards and the graphics in Core Ultra chips from "
     "Meteor Lake to Panther Lake. Arc G3 handheld chips aren't named in the notes, so check your maker's page first.",
     [("Release notes (PDF)", "https://downloadmirror.intel.com/930514/ReleaseNotes_101.9150_WHQL.pdf"),
      ("Download page", "https://www.intel.com/content/www/us/en/download/785597/intel-arc-graphics-windows.html")]),
    ("NVIDIA · GeForce", "Game Ready driver", "621.01", "WHQL", "21 Oct 2026",
     "Game Ready for Phantom Blade Zero, with DLSS 4.5 and path tracing, and adds Advanced Shader Delivery for "
     "Call of Duty: Modern Warfare 4 and Gears of War: E-Day.",
     [("Announcement", "https://www.nvidia.com/en-us/geforce/news/phantom-blade-zero-nvidia-geforce-game-ready-driver/"),
      ("Download page", "https://www.nvidia.com/en-us/geforce/drivers/")]),
]
CHIPSET = ("AMD · Ryzen", "Mobile chipset drivers", "8.09.28.1124", None, "21 Oct 2026",
           "For Ryzen handhelds, laptops and mini PCs. If your maker publishes its own chipset package, start there.",
           [("Release notes", "https://www.amd.com/en/resources/support-articles/release-notes/RN-RYZEN-CHIPSET-8-09-28-1124.html"),
            ("Download page", "https://www.amd.com/en/support/downloads/drivers.html/chipsets/laptop-chipsets/amd-ryzen-and-athlon-mobile-chipset.html")])
MAKERS = [  # (maker, page, url)
    ("ASUS", "ROG Xbox Ally (2025)", "https://rog.asus.com/us/gaming-handhelds/rog-ally/rog-xbox-ally-2025/helpdesk_download/"),
    ("ASUS", "ROG Xbox Ally X (2025)", "https://rog.asus.com/us/gaming-handhelds/rog-ally/rog-xbox-ally-x-2025/helpdesk_download/"),
    ("ASUS", "ROG Xbox Ally X20 (2026)", "https://rog.asus.com/us/gaming-handhelds/rog-ally/rog-xbox-ally-x20-2026/helpdesk/"),
    ("Lenovo", "Legion Go", "https://pcsupport.lenovo.com/us/en/products/laptops-and-netbooks/legion-series/legion-go-8apu1/downloads/driver-list/"),
    ("Lenovo", "Legion Go 2", "https://pcsupport.lenovo.com/us/en/products/laptops-and-netbooks/legion-series/legion-go-8ahp2/downloads"),
    ("Lenovo", "Legion Go S", "https://pcsupport.lenovo.com/us/en/products/laptops-and-netbooks/legion-series/legion-go-s-8apu1/83n6/downloads"),
    ("MSI", "Claw series: latest updates", "https://www.msi.com/Handheld/Recommended-For-Claw/latest-updates"),
    ("MSI", "All Claw models: pick yours, then Support", "https://www.msi.com/Handhelds"),
    ("OneXPlayer", "Drivers and FAQs for every model", "https://onexplayerstore.com/pages/drivers-and-faqs"),
    ("AYANEO", "Support downloads for every model", "https://ayaneo.com/support/download"),
    ("GPD", "GPD Win 5 drivers and firmware", "https://www.gpd.hk/gpdwin5firmwaredriver"),
]
TOOLS = [  # (anchor, group, [(name, owner/repo, description)])
    ("windows", "Windows handhelds", [
        ("Handheld Companion", "Valkirie/HandheldCompanion",
         "A touch-friendly overlay for Windows handhelds, with controller emulation, gyro aiming and performance controls."),
        ("Universal x86 Tuning Utility", "JamesCJ60/Universal-x86-Tuning-Utility",
         "Sets power limits (TDP) and clocks on AMD and Intel chips."),
        ("RyzenAdj", "FlyGoat/RyzenAdj", "A command-line tool that reads and sets power limits on Ryzen mobile chips.")]),
    ("cleanup", "Windows clean-up", [
        ("WinUtil by Chris Titus Tech", "ChrisTitusTech/winutil",
         "One window for installing programs, removing bloat, applying tweaks and fixes, and managing Windows updates. "
         "It runs from an admin PowerShell, so read the README first."),
        ("Win11Debloat by Raphire", "Raphire/Win11Debloat",
         "A PowerShell script that removes preinstalled apps, turns off telemetry and declutters Windows 10 and 11. "
         "Its wiki explains how to undo changes, and most removed apps can be reinstalled from the Microsoft Store.")]),
    ("linux", "SteamOS and Linux", [
        ("Bazzite", "ublue-os/bazzite",
         "A Fedora-based gaming Linux with SteamOS-style versions for handhelds, desktops and living-room PCs."),
        ("Decky Loader", "SteamDeckHomebrew/decky-loader", "Adds a plugin menu to Steam's Game Mode."),
        ("SimpleDeckyTDP", "aarron-lee/SimpleDeckyTDP", "A Decky plugin for TDP and power settings on Linux handheld PCs."),
        ("InputPlumber", "ShadowBlip/InputPlumber", "A Linux service that routes and remaps controller inputs on handhelds.")]),
    ("android", "Android", [
        ("DroidDeck", "Droid-Deck/DroidDeck",
         "Runs Valve's Steam client on Android handhelds, with Windows games through ARM64 Proton. It needs Android 9 or "
         "newer and an Adreno 730 or newer GPU. There's no official DroidDeck website, so only download it from GitHub. "
         "It isn't affiliated with Valve."),
        ("ARMSX2", "ARMSX2/ARMSX2",
         "A PlayStation 2 emulator for ARM64, based on PCSX2, for Android, iOS, Linux, macOS and Windows. Its own site is "
         "armsx2.net. Other sites with similar names aren't the project's, so download it from GitHub or armsx2.net."),
        ("ARMSX3", "ARMSX2/ARMSX3",
         "An early PlayStation 3 emulator for Android, built on RPCS3 by the ARMSX2 team. It's also on Google Play from "
         "the developer ARMSX. It needs a fast Snapdragon handheld (Snapdragon 8 Gen 2 or newer and 12GB of RAM are "
         "recommended), and you supply the PS3 firmware yourself.")]),
    ("upscaling", "Upscaling", [
        ("OptiScaler", "optiscaler/OptiScaler",
         "Swaps a game's upscaler for another one (DLSS, FSR or XeSS) and can add frame generation."),
        ("DLSS Swapper", "beeradmoore/dlss-swapper",
         "Manages and swaps the DLSS, FSR and XeSS files in games across the main PC launchers."),
        ("HelixSR", "lonewolf0622/HelixSR",
         "A drop-in FSR 3.1 replacement for DirectX 12 games that runs DLSS's upscaling network on AMD GPUs, also usable "
         "through OptiScaler. Version 1.2.0 builds the network from NVIDIA's DLSS DLL on your PC; the files it makes are "
         "for your own PC only. The author has tested it only on Linux, so treat it as experimental.")]),
    ("tweaks", "Stutter and HDR", [
        ("SCSKiller", "BlueHeisenberg/SCSKiller",
         "Shader Stutter Killer: compiles a game's shaders into the graphics driver's cache before you play. Windows, "
         "NVIDIA and AMD only, for DirectX 12 games (and DirectX 11 on NVIDIA). It doesn't fix traversal stutter, and a "
         "driver update means compiling again."),
        ("Go2HDR", "Rayekkk/Go2HDR",
         "A tray app for the Legion Go 2 that matches Windows' SDR content brightness to the screen brightness whenever HDR "
         "is on, using a curve you can edit."),
        ("LaptopTrueHDR", "spiwar/LaptopTrueHDR",
         "Calibrates Windows HDR for a laptop's or handheld's built-in screen: it reads the panel's peak brightness and "
         "sets the SDR/HDR content brightness to match. Run it at full system brightness with external screens unplugged, "
         "and delete any Windows HDR Calibration profiles first.")]),
]
MEASURE = [  # (name, shown address, url, description)
    ("CapFrameX", "github.com/CXWorld/CapFrameX", "https://github.com/CXWorld/CapFrameX",
     "Records and analyses frame times, with an overlay and comparison charts. It records the frame data in my runs."),
    ("PresentMon", "github.com/GameTechDev/PresentMon", "https://github.com/GameTechDev/PresentMon",
     "Intel's open-source frame-timing capture tool for Windows. CapFrameX captures through it."),
    ("HWiNFO64", "hwinfo.com", "https://www.hwinfo.com/download/",
     "Sensor readings and logging. I log every run with it, with its own FPS counter switched off."),
    ("RivaTuner Statistics Server", "guru3d.com", "https://www.guru3d.com/download/rtss-rivatuner-statistics-server-download/",
     "Draws the on-screen overlay in my runs."),
]

# ================================================================ videos
# data/videos.json: {"checked": ISO date, "videos": [{"id", "title" (as on YouTube), "published" (UTC date),
# "seconds", "views"}]}. Long-form only; Shorts are linked, not listed.
VDATA = json.loads((SRC / "data" / "videos.json").read_text())
EXPORT_DATE = show(VDATA["checked"])

# One line per long-form video, in Nizzel's words from that video's YouTube description (lightly trimmed).
BLURBS = {
    "CsgpuSEVITI": "Can Intel's new Arc G3 Extreme run Gears of War: E-Day on the OneXPlayer X2? Ten benchmark configurations from 30W to 40W, all tested at about 35,000 feet aboard an aircraft.",
    "2viMjdGRkS8": "What better place to play ACE COMBAT 8: Wings of Theve than at 35,000 feet? The AYANEO NEXT 2 from 35W to 85W, looking for the best balance between performance and power consumption.",
    "W3qXobq1-J4": "Power it. Dock it. Take it with you. Charging, Frost Bay cooling, three docks and two ways to carry the X2 Mini Pro.",
    "lY5GZKr9Pgk": "Setting up the X2 Mini Pro: Windows and driver updates, personalizing it, and three storage upgrades tested against the internal NVMe SSD.",
    "fJv2T-K8erI": "Same GPU. Half the CPU. Better screen, on paper. The X2 Mini Pro (Ryzen AI Max+ 388) meets the OneXFly Apex (Ryzen AI Max+ 395) on one table, one scale, one set of calipers.",
    "9iaiNM9KJIY": "Stuck at the airport with time to kill? Out came the OneXPlayer 3, and waiting for a flight became a gaming session.",
    "tAnlywbOgiw": "A dbrand skin cut for the Legion Go 2, on the OneXPlayer 3. It doesn't fit. The rest is salvage.",
    "5WGPiqBJtKw": "The AYANEO NEXT 2 at 85W on an actual plane, then straight into Onimusha: Way of the Sword.",
    "YhhXa0mJcKE": "The Next 2 couldn't hold 85W plugged in during my review. A viewer's comment sent me back to the bench, and one small change made the difference.",
    "VLbzPP-Wq-g": "Three handhelds. One Intel Arc G3 Extreme platform. Very different reasons to buy.",
    "oI6M0GXJS60": "Is the OneXFly Apex really as performant as an RTX 4060? One handheld against a complete desktop RTX 4060 eGPU chain, measured from the wall across synthetics, AI, creator work and eleven games.",
    "R5NCfNJm3Ak": "The AYANEO NEXT 2 on a flight, recorded locally through OBS Studio and played entirely on battery at a 55W power limit.",
    "P95qqjbJaFY": "I paid $398 for the Xtra Muse, the pocket gimbal camera The Verge's teardown found to be a DJI Osmo Pocket 3 in everything but name, and tested the twin theory the hard way.",
    "2iYgc9XRR8U": "The Ayn Thor Max in the setting it was built for: a hotel room, mid-trip, three thousand kilometers from my bench.",
    "zFT0b6o0Ap0": "Same chip, Ryzen AI Max+ 395 in both. So why does one of these handhelds complete every single benchmark while the other can't finish the test?",
    "E6MmVNjsn2E": "A quick preview cut, made before my full method was locked. The controlled retest is “I Got It Wrong. So I Tested Everything Again”.",
    "GNwvNYdnEZA": "The AYANEO NEXT 2 lands, bought at full price as backer number 4 on the campaign. No sample unit, no sponsorship, no strings.",
    "rSvfg-ltLC8": "Intel is back in the handheld fight. The OneXPlayer X2 is the first big-screen handheld on Intel's Arc G3 Extreme.",
    "9sxy1SWTXe8": "Three upgrades in one sitting, plus a DIY bonus build: the storage and capture pipeline rebuilt, with the PCIe lane details most upgrade videos skip.",
    "vcEb5bAYO1k": "Not a Steam Deck rival: a Strix Halo workstation with joysticks. My whole creator pipeline, from capture to 4K editing to a 70-billion-parameter AI model, off an 8-inch handheld.",
    "TD_gO9E-Ju0": "Welcome to my first video. It took 60-plus deleted recordings, 25 thumbnails and six to eight weeks of work to get here.",
}

# Companion pages: videos whose numbers are published here. Text is from each video's own description.
VIDEO_PAGES = {
    "YhhXa0mJcKE": {
        "file": "video-ayaneo-next-2-85w.html", "published": "2026-09-06T00:24:08Z", "iso": "PT28M2S",
        "intro": [
            "The AYANEO Next 2 couldn't hold 85W plugged in during my review. A viewer's comment sent me back to the "
            "bench, and one small change made the difference.",
            "Four games didn't finish at the 85W plugged-in tier in the original review: power dropped to 55W or "
            "disconnected. Other owners hit the same thing, and some shared what worked for them. So I updated "
            "everything, set up four power configurations and re-ran the test on my unit before a flight. Huge thanks "
            "to Squallnine for the testing, the recommendations, and for pushing me to look again.",
            "Two things to be clear about: this was a quick replication, not a multi-hour soak. And the review's DNFs "
            "still stand, because that's the out-of-box experience. But if your Next 2 is dropping to 55W, there's an "
            "inexpensive change worth trying before anything else."],
        "tested": [
            "Fresh updates first: AMD Adrenalin, AMD chipset and AYANEO firmware",
            "Stock charger and stock cable at 85W",
            "Stock charger with a 240W USB-C cable",
            "Anker Prime 160W (PD 3.1) with a 240W USB-C (Thunderbolt 5) cable",
            "CUKTECH No. 30 300W desktop station with its own cable",
            "Game: Crimson Desert, Medium preset, FSR 4.1, frame generation 2X"],
        "chapters": [(0, "Recap, and thanks to Squallnine"), (42, "The gear on the table"), (95, "Updates first"),
                     (115, "Stock charger and stock cable"), (405, "The power drop on the stock charger and cable"),
                     (412, "Anker 160W with the 240W cable"), (796, "Anker Prime firmware updated, test starts"),
                     (1055, "Anker Prime 160W through the UGREEN dock"), (1110, "CUKTECH 300W"), (1559, "Outro")],
        "devices": [("H15", "AYANEO Next 2"), ("P01", "Anker Prime charger"), ("P02", "CUKTECH 30 Ultra charger")],
        "note": "Everything in this video was bought with my own money. No sponsorships or gifts.",
    },
    "VLbzPP-Wq-g": {
        "file": "video-g3e-family-feud.html", "published": "2026-09-05T15:08:44Z", "iso": "PT28M33S",
        "intro": [
            "Three handhelds. One Intel Arc G3 Extreme platform. Very different reasons to buy.",
            "The OneXFly Apex Air, the OneXPlayer X2 and the OneXPlayer 3, set up the same way and tested at the same "
            "35W and 40W targets, with a separate 45W pass on the Apex Air.",
            "546 scored runs across 11 games, two power profiles, acoustics and wall power. The performance gap is 1 to "
            "3 fps in most games, and 5% at the very worst. So the real fight is everything else: weight (measured on "
            "my scale, not spec sheets), screen, noise, battery and price. The buyer matrix crowns a winner."],
        "tested": [
            "3DMark synthetic tests and an 11-game suite",
            "CapFrameX averages, 1% lows and 0.2% lows",
            "Whole-device wall power",
            "Near-field noise",
            "Screens, battery, weight and form factor"],
        "chapters": [(0, "Intro"), (102, "Unboxing the OneXPlayer 3"), (220, "Unboxing the OneXFly Apex Air"),
                     (313, "Wait, there's a third device?"), (416, "Standardising the setup"),
                     (471, "Workflow and wall-power draw"), (555, "The 40W update"), (631, "Synthetic benchmarks"),
                     (687, "Gaming benchmarks"), (766, "Results, buyer matrix and conclusion")],
        "devices": [("H11", "OneXPlayer 3"), ("H10", "OneXPlayer X2"), ("H14", "OneXFly Apex Air")],
        "note": "I paid for and own all three devices. No sponsorship, no review units.",
    },
}

def clean_title(t):
    t = t.split("\n")[0]
    t = re.sub(r"\s*#\S+", "", t)
    t = re.sub(r"\s{2,}", " ", t).strip()
    t = re.sub(r"\s*[—–-]\s*$", "", t).strip()
    return re.sub(r"(\w)—(\w)", r"\1: \2", t)      # "Feud—Same" reads better as "Feud: Same"

def fmt_dur(s):
    h, rem = divmod(int(s), 3600)
    m, sec = divmod(rem, 60)
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"

def day(d):
    return f"{d.day} {d:%b %Y}"

def yt(vid):
    return f"https://www.youtube.com/watch?v={vid}"

def load_videos():
    """Long-form public videos (over three minutes), newest first."""
    out = []
    for v in VDATA["videos"]:
        if v["seconds"] > 180:
            out.append({"id": v["id"], "title": clean_title(v["title"]), "dur": v["seconds"], "views": v["views"],
                        "date": datetime.strptime(v["published"], "%Y-%m-%d")})
    return sorted(out, key=lambda v: v["date"], reverse=True)

VIDEOS = load_videos()
VBYID = {v["id"]: v for v in VIDEOS}

# ================================================================ results
RESULT_TYPES = ["Handhelds", "Emulation", "eGPUs", "Mini PCs"]
RESULTS = [
    {"slug": "x2-ps3-rpcs3", "type": "Emulation", "video": None, "tag": ("t-warn", "Preliminary"),
     "title": "PS3 emulation on the OneXPlayer X2",
     "finding": "11 of 14 games passed gameplay and save/load in RPCS3. Uncharted 3 and The Last of Us kept freezing. Check that Turbo (CPU Boost) is on.",
     "meta": "Oct 2026 · RPCS3 0.0.43, 40W, 720p",
     "mini": ('<ul class="checks">'
              '<li><span>Passed gameplay and save/load</span><span class="res res-ok"><span aria-hidden="true">✓</span> 11</span></li>'
              '<li><span>Gameplay passed, save/load unchecked</span><span class="res res-warn"><span aria-hidden="true">?</span> 1</span></li>'
              '<li><span>Unresolved: repeated freezes</span><span class="res res-bad"><span aria-hidden="true">✕</span> 2</span></li>'
              '</ul>')},
    {"slug": "eday-g3e", "type": "Handhelds", "video": "CsgpuSEVITI", "tag": ("t-gold", "Verdict"),
     "title": "Gears of War: E-Day on the OneXPlayer X2",
     "finding": "40W, Low, frame generation off: 65 fps average, 48 fps 1% low, no stutter. Frame generation lifts the average but the lows fall.",
     "meta": "Oct 2026 · 10 configurations, 30W to 40W, XeSS Dynamic",
     "mini": ('<ul class="bars">'
              '<li><div class="bar-top"><span>40W Low, FG off<small>1% low 48</small></span><b>65</b></div><div class="track" aria-hidden="true"><span class="fill" style="width:81.3%"></span></div></li>'
              '<li><div class="bar-top"><span>40W Medium, FG off<small>1% low 45</small></span><b>49</b></div><div class="track" aria-hidden="true"><span class="fill" style="width:61.3%"></span></div></li>'
              '<li><div class="bar-top"><span>40W Medium, FG 2x<small>1% low 32</small></span><b>73</b></div><div class="track" aria-hidden="true"><span class="fill" style="width:91.3%"></span></div></li>'
              '</ul><p class="cap">Average fps. Bars run from 0 to 80 fps.</p>')},
    {"slug": "x2minipro-vs-apex-physical", "type": "Handhelds", "video": "fJv2T-K8erI", "tag": ("t-ok", "Verified"),
     "title": "X2 Mini Pro vs OneXFly Apex, Part 1",
     "finding": "The Apex is 70.7 g lighter ready to play and smaller. The Mini Pro has the bigger 8.84-inch screen, a lighter charger and a longer cable, and it passed 3 of 4 USB-C charger tests to the Apex's 2.",
     "meta": "Sep 2026 · Weight, size, chargers, and temps and noise at 55W",
     "mini": ('<ul class="checks">'
              '<li><span>Lighter and smaller</span><span class="res res-ok">Apex</span></li>'
              '<li><span>Bigger screen, 8.84" vs 8.02"</span><span class="res res-ok">Mini Pro</span></li>'
              '<li><span>More USB-C charger tests passed</span><span class="res res-ok">Mini Pro</span></li>'
              '</ul>')},
    {"slug": "next2-85w", "type": "Handhelds", "video": "YhhXa0mJcKE", "tag": ("t-ok", "Verified"),
     "title": "Can the AYANEO Next 2 hold 85W plugged in?",
     "finding": "It held 85W in 3 of 4 charger and cable setups. On my unit, the stock cable was the limit.",
     "meta": "Sep 2026 · Crimson Desert, Medium, FSR 4.1, frame generation 2X",
     "mini": ('<ul class="checks">'
              '<li><span>Stock charger, stock cable</span><span class="res res-bad"><span aria-hidden="true">✕</span> Didn\'t hold</span></li>'
              '<li><span>Stock charger, 240W cable</span><span class="res res-ok"><span aria-hidden="true">✓</span> Held</span></li>'
              '<li><span>Anker Prime 160W, 240W cable</span><span class="res res-ok"><span aria-hidden="true">✓</span> Held</span></li>'
              '<li><span>CUKTECH 30 Ultra, its own cable</span><span class="res res-ok"><span aria-hidden="true">✓</span> Held</span></li>'
              '</ul>')},
    {"slug": "g3e-family-feud", "type": "Handhelds", "video": "VLbzPP-Wq-g", "tag": ("t-gold", "Verdict"),
     "title": "G3E Family Feud: three Arc G3 Extreme handhelds",
     "finding": "The OneXPlayer 3 tops my buyer score at 88, and it's the lightest of the three at 940 g.",
     "meta": "Sep 2026 · 546 scored runs, 11 games, 35W and 40W",
     "mini": ('<ul class="bars">'
              '<li><div class="bar-top"><span>OneXPlayer 3</span><b>88</b></div><div class="track" aria-hidden="true"><span class="fill" style="width:100%"></span></div></li>'
              '<li><div class="bar-top"><span>OneXPlayer X2</span><b>78.5</b></div><div class="track" aria-hidden="true"><span class="fill" style="width:89.2%"></span></div></li>'
              '<li><div class="bar-top"><span>OneXFly Apex Air</span><b>73.5</b></div><div class="track" aria-hidden="true"><span class="fill" style="width:83.5%"></span></div></li>'
              '</ul><p class="cap">My weighted buyer score, in points. Bars start at zero.</p>')},
    {"slug": "apex-vs-rtx4060", "type": "eGPUs", "video": "oI6M0GXJS60", "tag": ("t-ok", "Verified"),
     "title": "OneXFly Apex vs an RTX 4060 eGPU setup",
     "finding": "At native 1440p the Apex averaged 74.5 fps across 10 games to the RTX 4060 setup's 70.7. With path-traced Wukong, the RTX 4060 was 70% faster.",
     "meta": "Aug 2026 · 1440p, wall power, three runs, medians",
     "mini": ('<ul class="bars">'
              '<li><div class="bar-top"><span>Apex, native<small>10-game average</small></span><b>74.5</b></div><div class="track" aria-hidden="true"><span class="fill" style="width:93.1%"></span></div></li>'
              '<li><div class="bar-top"><span>RTX 4060, native<small>10-game average</small></span><b>70.7</b></div><div class="track" aria-hidden="true"><span class="fill" style="width:88.4%"></span></div></li>'
              '<li><div class="bar-top"><span>Apex, Wukong full RT</span><b>23.9</b></div><div class="track" aria-hidden="true"><span class="fill" style="width:29.9%"></span></div></li>'
              '<li><div class="bar-top"><span>RTX 4060, Wukong full RT</span><b>40.5</b></div><div class="track" aria-hidden="true"><span class="fill" style="width:50.6%"></span></div></li>'
              '</ul><p class="cap">Average fps. Bars run from 0 to 80 fps.</p>')},
]

def plate(r, page_link=True):
    t = (W / "results" / f"{r['slug']}.html").read_text()
    t = t.replace('<article class="plate"', f'<article class="plate" id="{r["slug"]}"', 1)
    vp = VIDEO_PAGES.get(r["video"])
    link = f' · <a href="{vp["file"]}">Video page →</a>' if (page_link and vp) else ""
    return t.replace("%%PAGE_LINK%%", link)

def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")

# ================================================================ shared chrome
NAV = [("videos", "Videos", "videos.html"), ("results", "Results", "results.html"), ("method", "Method", "method.html"),
       ("bench", "Bench", "bench.html"), ("news", "News", "news.html"), ("links", "Links", "links.html"),
       ("about", "About", "about.html")]

def topbar(current):
    cur = ' aria-current="page"'
    items = "\n      ".join(f'<a href="{href}"{cur if key == current else ""}>{label}</a>' for key, label, href in NAV)
    brand = "#top" if current == "home" else "./"
    return f"""<header class="topbar">
  <div class="wrap">
    <a class="brand" href="{brand}" aria-label="No_Tech-Dad, home"><img src="img/badge.png" width="34" height="34" alt="">No_Tech-Dad</a>
    <nav class="nav" aria-label="Pages">
      {items}
    </nav>
    <a class="btn btn-red btn-sm" href="{SUBSCRIBE}" target="_blank" rel="noopener">Subscribe</a>
  </div>
</header>"""

def footer():
    return f"""<footer class="foot" id="contact">
  <div class="wrap">
    <div class="foot-grid">
      <div class="foot-brand">
        <span class="brand"><img src="img/badge.png" width="48" height="48" alt="">No_Tech-Dad</span>
        <p class="tagline-sm">Tech. Life. Leveling Up Together.</p>
        <p>Independent tests of handheld PCs, eGPUs and mini PCs. Run by a human, supported by AI.</p>
      </div>
      <div>
        <h2 class="subhead-label">Find me</h2>
        <ul class="links">
          <li><span class="lk">Email</span><span class="val"><a id="foot-email" href="mailto:{EMAIL}">{EMAIL}</a><button class="copy" type="button" data-copy="{EMAIL}" aria-controls="foot-email"><span class="copy-label">Copy</span></button></span></li>
          <li><span class="lk">YouTube</span><a href="{CHANNEL}" target="_blank" rel="noopener">@no_tech-dad ↗</a></li>
          <li><span class="lk">X</span><a href="https://x.com/No_TechDad" target="_blank" rel="noopener">@No_TechDad ↗</a></li>
          <li><span class="lk">Discord</span><span class="val"><span id="discord-handle">nizzel1982</span><button class="copy" type="button" data-copy="nizzel1982" aria-controls="discord-handle"><span class="copy-label">Copy</span></button></span></li>
          <li><span class="lk">Community</span><a href="https://handheldsunited.com" target="_blank" rel="noopener">Handhelds United ↗</a></li>
        </ul>
      </div>
    </div>
    <div class="fine">
      <span>I buy everything I review with my own money, and the opinions are my own.</span>
      <span>Stay healthy. Stay safe. Love and peace. · Updated {UPDATED}</span>
    </div>
  </div>
</footer>"""

SCRIPT = """<script>
(function () {  // on phones the nav scrolls sideways: bring the current page's item into view
  var cur = document.querySelector('.nav [aria-current="page"]');
  if (!cur) return;
  var nav = cur.parentElement, r = cur.getBoundingClientRect(), n = nav.getBoundingClientRect();
  if (r.right > n.right) nav.scrollLeft += r.right - n.right + 8;
})();
document.querySelectorAll('img[data-yt]').forEach(function (img) {
  var drop = function () { img.remove(); };
  if (img.complete && img.naturalWidth === 0) { drop(); } else { img.addEventListener('error', drop); }
});
document.querySelectorAll('[data-embed]').forEach(function (box) {
  // Plays the video in place on notechdad.com; anywhere else the link simply opens YouTube.
  if (!/(^|\\.)notechdad\\.com$/.test(location.hostname)) return;
  box.querySelector('a').addEventListener('click', function (ev) {
    ev.preventDefault();
    var f = document.createElement('iframe');
    f.src = 'https://www.youtube-nocookie.com/embed/' + box.getAttribute('data-embed') + '?autoplay=1&rel=0';
    f.title = box.getAttribute('data-title') || 'YouTube video';
    f.allow = 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share';
    f.setAttribute('allowfullscreen', '');
    f.setAttribute('referrerpolicy', 'strict-origin-when-cross-origin');
    box.replaceChildren(f);
  });
});
document.querySelectorAll('[data-copy]').forEach(function (btn) {
  btn.addEventListener('click', function () {
    var label = btn.querySelector('.copy-label');
    var reset = function () { setTimeout(function () { label.textContent = 'Copy'; }, 2200); };
    function selectIt() {
      var el = document.getElementById(btn.getAttribute('aria-controls'));
      try {
        var range = document.createRange(); range.selectNodeContents(el);
        var sel = window.getSelection(); sel.removeAllRanges(); sel.addRange(range);
        label.textContent = 'Selected';
      } catch (e2) { label.textContent = 'Copy failed'; }
      reset();
    }
    try {
      navigator.clipboard.writeText(btn.getAttribute('data-copy')).then(function () {
        label.textContent = 'Copied'; reset();
      }, selectIt);
    } catch (e) { selectIt(); }
  });
});
</script>"""

# ================================================================ components
PLAY = ('<span class="play" aria-hidden="true"><svg viewBox="0 0 24 24" width="28" height="28" focusable="false">'
        '<path d="M8 5.5v13l10.5-6.5z" fill="currentColor"/></svg></span>')

def vthumb(v, big=False, newest=False):
    if big:
        img = (f'<img data-yt src="https://i.ytimg.com/vi/{v["id"]}/maxresdefault.jpg" alt="" width="1280" height="720"'
               f' fetchpriority="high">')
        tag = '<span class="vf-tag"><i class="dot" aria-hidden="true"></i>Newest</span>' if newest else ""
        extra = f'<span class="vf"></span>{PLAY}{tag}<span class="dur">{fmt_dur(v["dur"])}</span>'
        return f'<span class="vthumb big" aria-hidden="true"><span class="fb">No_Tech-Dad</span>{img}{extra}</span>'
    img = f'<img data-yt src="https://i.ytimg.com/vi/{v["id"]}/hqdefault.jpg" alt="" width="480" height="360" loading="lazy">'
    return f'<span class="vthumb" aria-hidden="true"><span class="fb">No_Tech-Dad</span>{img}</span>'

def video_card(v, with_blurb=False):
    vp = VIDEO_PAGES.get(v["id"])
    href = vp["file"] if vp else yt(v["id"])
    ext = "" if vp else ' target="_blank" rel="noopener"'
    go = "Video page and results →" if vp else "Watch on YouTube ↗"
    b = BLURBS.get(v["id"], "")
    blurb = f'<span class="vc-blurb">{e(b)}</span>' if (with_blurb and b) else ""
    return (f'        <li class="vc"><a href="{href}"{ext}>{vthumb(v)}'
            f'<span class="vc-title">{e(v["title"])}</span>'
            f'<span class="vc-meta"><time datetime="{v["date"]:%Y-%m-%d}">{day(v["date"])}</time> · {fmt_dur(v["dur"])}</span>'
            f'{blurb}<span class="vc-go">{go}</span></a></li>')

def driver_card(d):
    vendor, name, ver, status, date, note, links = d
    tag = f'<span class="tag t-plain">{e(status)}</span>' if status else ""
    lk = "".join(f'<a href="{e(u)}" target="_blank" rel="noopener">{e(l)} ↗</a>' for l, u in links)
    return (f'        <li class="drv"><p class="drv-vendor">{e(vendor)}</p><h3 class="drv-name">{e(name)}</h3>'
            f'<p class="drv-ver"><span class="v">{e(ver)}</span>{tag}</p><p class="drv-date">Released {e(date)}</p>'
            f'<p class="drv-note">{e(note)}</p><p class="drv-links">{lk}</p></li>')

def lrow(name, where, url, desc=""):
    d = f'<span class="lr-desc">{e(desc)}</span>' if desc else ""
    return (f'<li><a class="lrow" href="{e(url)}" target="_blank" rel="noopener">'
            f'<span class="lr-name">{e(name)}<span class="lr-go" aria-hidden="true"> ↗</span></span>'
            f'<span class="lr-where">{e(where)}</span>{d}</a></li>')

def page_head(eyebrow, title, lead="", jumps="", extra_cls=""):
    lead_html = f'\n    <p class="sec-lead">{lead}</p>' if lead else ""
    jump_html = f'\n    <ul class="jump">{jumps}</ul>' if jumps else ""
    cls = f"page-head {extra_cls}".strip()
    return f"""  <div class="{cls}">
    <p class="eyebrow">{eyebrow}</p>
    <h1>{e(title)}</h1>{lead_html}{jump_html}
  </div>"""

def section(sid, title, lead, inner, n, unit=("entry", "entries")):
    lead_html = f'<p class="sec-lead">{e(lead)}</p>' if lead else ""
    count_html = f'<span class="count">{n} {unit[0] if n == 1 else unit[1]}</span>' if n is not None else ""
    return (f'  <section class="inv-sec" id="{sid}" aria-labelledby="{sid}-title">\n'
            f'    <div class="inv-head"><h2 id="{sid}-title">{e(title)}</h2>{count_html}</div>\n'
            f'    {lead_html}{inner}\n  </section>')

# ================================================================ home
def feature(v):
    vp = VIDEO_PAGES.get(v["id"])
    second = (f'<a class="btn btn-line" href="{vp["file"]}">Results and notes</a>' if vp
              else '<a class="btn btn-line" href="videos.html">All videos</a>')
    return f"""        <article class="feature" aria-labelledby="feat-title">
          <a class="feature-media" href="{yt(v['id'])}" target="_blank" rel="noopener" aria-label="Watch {e(v['title'])} on YouTube">{vthumb(v, big=True, newest=True)}</a>
          <p class="feat-kicker">Newest video · <time datetime="{v['date']:%Y-%m-%d}">{day(v['date'])}</time></p>
          <h2 class="feat-title" id="feat-title">{e(v['title'])}</h2>
          <p class="feat-blurb">{e(BLURBS.get(v['id'], ''))}</p>
          <div class="cta"><a class="btn btn-red" href="{yt(v['id'])}" target="_blank" rel="noopener">Watch on YouTube ↗</a>{second}</div>
        </article>"""

def ledger():
    items = [("bench.html", str(ON_BENCH), "devices on the bench"),
             ("about.html", "100%", "bought with my own money"),
             ("method.html", "3", "runs before any summary number"),
             ("videos.html", str(len(VIDEOS)), "long-form videos")]
    lis = "".join(f'<li><a href="{h}"><b>{n}</b><span>{e(t)}</span></a></li>' for h, n, t in items)
    return f"""  <section class="ledger" aria-label="The channel in numbers">
    <div class="wrap"><ul>{lis}</ul></div>
  </section>"""

def result_card(r):
    vp = VIDEO_PAGES.get(r["video"])
    tcls, tlabel = r["tag"]
    links = f'<a href="results.html#{r["slug"]}">Full result →</a>'
    if vp:
        links += f'<a href="{vp["file"]}">Video page →</a>'
    return f"""        <article class="rcard" aria-labelledby="rs-{r['slug']}">
          <div class="rs-tags"><span class="tag t-plain">{e(r['type'])}</span><span class="tag {tcls}">{tlabel}</span></div>
          <h3 id="rs-{r['slug']}">{e(r['title'])}</h3>
          <p class="finding">{e(r['finding'])}</p>
          {r['mini']}
          <p class="rs-meta">{e(r['meta'])}</p>
          <p class="rs-links">{links}</p>
        </article>"""

def result_types():
    return [t for t in RESULT_TYPES if any(r["type"] == t for r in RESULTS)]

def results_hub():
    cards = "\n".join(result_card(r) for r in RESULTS)
    eyebrow = f"{len(RESULTS)} results · " + ", ".join(result_types())
    return f"""  <section class="sec" id="results" aria-labelledby="results-title">
    <div class="wrap">
      <div class="sec-head">
        <div>
          <p class="eyebrow">{e(eyebrow)}</p>
          <h2 id="results-title">Results</h2>
          <p class="sec-lead">Numbers from the videos, each with the conditions it was measured under and grouped by device type. More go up as each project's workbook is locked.</p>
        </div>
        <a class="more" href="results.html">All results →</a>
      </div>
      <div class="rgrid">
{cards}
      </div>
    </div>
  </section>"""

def latest_section():
    cards = "\n".join(video_card(v) for v in VIDEOS[1:7])
    return f"""  <section class="sec sec-alt" id="videos" aria-labelledby="videos-title">
    <div class="wrap">
      <div class="sec-head">
        <div>
          <p class="eyebrow">{len(VIDEOS)} videos · checked {EXPORT_DATE}</p>
          <h2 id="videos-title">Latest videos</h2>
          <p class="sec-lead">New videos land on YouTube first. The ones with a page here carry their numbers, test conditions and chapters.</p>
        </div>
        <a class="more" href="videos.html">All videos →</a>
      </div>
      <ul class="vgrid2">
{cards}
      </ul>
    </div>
  </section>"""

def drivers_mini():
    rows = []
    for vendor, name, ver, status, date, note, links in DRIVERS:
        dl = dict(links)["Download page"]
        short = vendor.split(" · ")[0]
        st = f" · {e(status)}" if status else ""
        rows.append(f'<li><span class="dm-name"><b>{e(short)}</b>{e(name)}</span><span class="dm-ver">{e(ver)}</span>'
                    f'<span class="dm-sub">{e(date)}{st} · <a href="{e(dl)}" target="_blank" rel="noopener">Download ↗</a></span></li>')
    return ('          <ul class="dmini">' + "".join(rows) + "</ul>\n"
            '          <p class="dm-note">On a handheld PC? Get its drivers from the maker first: '
            '<a class="inline" href="links.html#makers">maker support pages</a>.</p>')

def home_main():
    return (part("home.html")
            .replace("%%FEATURE%%", feature(VIDEOS[0]))
            .replace("%%LEDGER%%", ledger())
            .replace("%%RESULTS_HUB%%", results_hub())
            .replace("%%LATEST%%", latest_section())
            .replace("%%DRIVERS_MINI%%", drivers_mini())
            .replace("%%LINKS_DATE%%", LINKS_DATE)
            .replace("%%NEWS_DATE%%", NEWS_DATE))

# ================================================================ pages
def videos_main():
    top = sorted(VIDEOS, key=lambda v: -v["views"])[:3]
    most = "\n".join(video_card(v, True) for v in top)
    allv = "\n".join(video_card(v, True) for v in VIDEOS)
    head = page_head(f"{len(VIDEOS)} videos · checked {EXPORT_DATE}", "Videos",
                     "Every long-form video on the channel, newest first. The ones with a page here carry their "
                     "numbers, test conditions and chapters. The rest open on YouTube.")
    shorts = (f'<p class="otw vshorts"><b>Shorts</b><a class="inline" href="{CHANNEL}/shorts" target="_blank" '
              f'rel="noopener">See the Shorts on YouTube ↗</a></p>')
    return f"""<main id="top">
<div class="wrap">
{head}
{section("most", "Most watched", "", f'<ul class="vgrid2">{chr(10)}{most}{chr(10)}      </ul>', None)}
{section("all", "All videos", "", f'<ul class="vgrid2">{chr(10)}{allv}{chr(10)}      </ul>' + shorts, len(VIDEOS), ("video", "videos"))}
</div>
</main>"""

def results_main():
    types = result_types()
    jumps = "".join(f'<li><a href="#type-{slugify(t)}">{e(t)} <b>{sum(r["type"] == t for r in RESULTS)}</b></a></li>'
                    for t in types)
    secs = []
    for t in types:
        rs = [r for r in RESULTS if r["type"] == t]
        secs.append(section(f"type-{slugify(t)}", t, "", '<div class="plates">' + "".join(plate(r) for r in rs) + "</div>",
                            len(rs), ("result", "results")))
    pending = [t for t in RESULT_TYPES if t not in types]
    pend = ""
    if pending:
        names = " and ".join({"eGPUs": "eGPU", "Mini PCs": "mini PC", "Handhelds": "handheld"}[t] for t in pending)
        pend = f'  <p class="held">{names} results go up here once their workbooks are locked.</p>\n'
    head = page_head(f"{len(RESULTS)} results · updated {UPDATED}", "Results",
                     'Numbers from the videos, each with the conditions it was measured under. Every claim carries a '
                     'label; <a class="inline" href="method.html">the method</a> explains them.', jumps)
    return f"""<main id="top">
<div class="wrap">
{head}
{chr(10).join(secs)}
{pend}</div>
</main>"""

def method_main():
    head = page_head("Test protocol", "Method",
                     "This is how the tests behind every result are run. Each claim on the channel carries one of the "
                     "labels below.")
    return f"""<main id="top">
<div class="wrap">
{head}
  <div class="method2">
    <section aria-labelledby="labels-title"><h2 class="subhead-label" id="labels-title">Labels</h2>
{part("method_legend.html")}    </section>
    <section aria-labelledby="proto-title"><h2 class="subhead-label" id="proto-title">Protocol</h2>
{part("method_proto.html")}    </section>
  </div>
  <p class="held">The capture tools are listed on the <a class="inline" href="links.html#measuring">links page</a>.</p>
</div>
</main>"""

def news_main():
    head = page_head(f"Checked {NEWS_DATE}", "Industry news",
                     "What's moving in handheld PCs, graphics and eGPUs. The summaries are mine. Specs, prices and "
                     "performance claims are the makers', retailers' and outlets' figures, and I haven't tested them. "
                     "Reports and rumors are labeled.")
    return f"""<main id="top">
<div class="wrap">
{head}
  <div class="news-page">
{part("news_body.html")}  </div>
</div>
</main>"""

def about_main():
    head = page_head("One person, supported by AI", "About")
    return f"""<main id="top">
<div class="wrap">
{head}
  <div class="about-page">
{part("about_body.html")}  </div>
</div>
</main>"""

def bench_main():
    def table(groups):
        rows_all = [r for _, rows in groups for r in rows]
        has_det = any(r[2] for r in rows_all)
        has_note = any(r[3] for r in rows_all)
        cols = ["Asset", "Device"] + (["Details"] if has_det else []) + (["Notes"] if has_note else [])
        head = "<thead><tr>" + "".join(f'<th scope="col">{c}</th>' for c in cols) + "</tr></thead>"
        bodies = []
        for label, rows in groups:
            trs = []
            if label:
                trs.append(f'<tr><th colspan="{len(cols)}" scope="colgroup">{e(label)}</th></tr>')
            for aid, dev, det, note in rows:
                tds = [f'<td class="asset">{aid}</td>', f'<td class="dev">{e(dev)}</td>']
                if has_det:
                    tds.append(f'<td class="det">{e(det)}</td>')
                if has_note:
                    tds.append(f'<td class="note">{e(note)}</td>')
                trs.append(f'<tr id="asset-{aid}">' + "".join(tds) + "</tr>")
            bodies.append("<tbody>" + "".join(trs) + "</tbody>")
        return f'<div class="tbl"><table class="inv">{head}{"".join(bodies)}</table></div>'

    hh_groups = []
    for vendor, archs in ARCH.items():
        for arch, note in archs:
            rows = [(d[0], d[1], d[2], d[5]) for d in HANDHELDS if d[3] == vendor and d[4] == arch]
            label = f"{vendor} · {arch}" + (f", {note}" if arch == "Gorgon Point" else "")
            hh_groups.append((label, rows))
    parts = [section("handhelds", "Handheld PCs", "Grouped by chip generation.", table(hh_groups), len(HANDHELDS))]
    for sid, title, lead, groups in SECTIONS:
        inner = table(groups)
        if sid == "filming":
            inner += f'<p class="sw"><b>Software</b>{e(SOFTWARE)}</p>'
        parts.append(section(sid, title, lead, inner, count(groups)))
    inc_rows = "".join(
        f'<tr id="asset-{a}"><td class="asset">{a}</td><td class="dev">{e(d)}</td><td class="det">{e(det)}</td>'
        f'<td><span class="tag {cls}">{e(st)}</span></td></tr>' for a, d, det, st, cls in INCOMING)
    inc = ('<div class="tbl"><table class="inv"><thead><tr><th scope="col">Asset</th><th scope="col">Device</th>'
           '<th scope="col">Details</th><th scope="col">Status</th></tr></thead><tbody>' + inc_rows + "</tbody></table></div>")
    parts.append(section("incoming", "On the way", "Bought or backed, and not on the bench yet.", inc, len(INCOMING)))
    jumps = [("handhelds", "Handheld PCs", len(HANDHELDS))] + [(s, t, count(g)) for s, t, _, g in SECTIONS] + [("incoming", "On the way", len(INCOMING))]
    jump_html = "".join(f'<li><a href="#{s}">{e(t)} <b>{n}</b></a></li>' for s, t, n in jumps)
    head = page_head(f"Updated {INV_DATE} · {ON_BENCH} entries on the bench", "Inventory",
                     "Everything here was bought with my own money. Asset numbers come from my inventory workbook. "
                     "Anything whose exact model I haven't confirmed yet stays off this list until I have.", jump_html)
    return f"""<main id="top">
<div class="wrap">
{head}
{chr(10).join(parts)}
  <p class="held">Spotted a wrong label? Email me at {EMAIL}.</p>
</div>
</main>"""

def link_jumps():
    return ([("drivers", "Graphics drivers", len(DRIVERS) + 1), ("makers", "Handheld makers", len(MAKERS))]
            + [(a, t, len(rows)) for a, t, rows in TOOLS] + [("measuring", "Measuring tools", len(MEASURE))])

def links_count():
    return len(DRIVERS) + 1 + len(MAKERS) + sum(len(t) for *_, t in TOOLS) + len(MEASURE)

def links_main():
    host = lambda u: urlparse(u).netloc.removeprefix("www.")
    jump_html = "".join(f'<li><a href="#{a}">{e(t)} <b>{n}</b></a></li>' for a, t, n in link_jumps())
    drv = '<ul class="drivers">\n' + "\n".join(driver_card(d) for d in DRIVERS + [CHIPSET]) + "\n      </ul>"
    makers = '<ul class="lrows">' + "".join(lrow(p, f"{m} · {host(u)}", u) for m, p, u in MAKERS) + "</ul>"
    groups = "".join(
        f'<h3 class="lgroup" id="{a}">{e(t)}</h3><ul class="lrows">'
        + "".join(lrow(n, f"github.com/{r}", f"https://github.com/{r}", d) for n, r, d in rows) + "</ul>"
        for a, t, rows in TOOLS)
    caution = ('<aside class="caution" aria-label="Before you install"><b>Before you install</b>These are community '
               "projects, not vendor software, so read each project's page first. On Windows, set a restore point before "
               "you change anything. Tools that change Windows settings or power limits can make a device unstable, "
               "and upscaler mods don't belong in online games with anti-cheat.</aside>")
    measure = '<ul class="lrows">' + "".join(lrow(n, w, u, d) for n, w, u, d in MEASURE) + "</ul>"
    n_tools = sum(len(t) for *_, t in TOOLS)
    parts = [
        section("drivers", "Graphics drivers",
                "If your handheld's maker publishes its own graphics driver, start there.", drv, len(DRIVERS) + 1),
        section("makers", "Handheld makers",
                "Drivers, BIOS and firmware updates for each device come from its maker.", makers, len(MAKERS)),
        section("tools", "Open-source tools", "Free projects on GitHub that I point handheld owners to.",
                caution + groups, n_tools),
        section("measuring", "Measuring tools", "The capture tools from my test method.", measure, len(MEASURE)),
    ]
    head = page_head(f"Checked {LINKS_DATE} · {links_count()} links", "Useful links",
                     f"Graphics drivers, handheld makers' support pages and the open-source tools I point people to. "
                     f"Versions and dates were correct on {LINKS_DATE}, and the official page always has the newest.",
                     jump_html)
    return f"""<main id="top">
<div class="wrap">
{head}
{chr(10).join(parts)}
  <p class="held">Know a link that belongs here? Email me at {EMAIL}.</p>
</div>
</main>"""

def ts(s):
    m, sec = divmod(s, 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m:02d}:{sec:02d}"

def companion_main(vid):
    v, p = VBYID[vid], VIDEO_PAGES[vid]
    rs = [r for r in RESULTS if r["video"] == vid]
    intro = "".join(f"<p>{e(x)}</p>" for x in p["intro"])
    chapters = "".join(f'<li><a href="{yt(vid)}&amp;t={s}s" target="_blank" rel="noopener"><time>{ts(s)}</time>'
                       f'<span>{e(label)}</span></a></li>' for s, label in p["chapters"])
    devices = "".join(f'<li><a href="bench.html#asset-{a}">{e(n)} <b>{a}</b></a></li>' for a, n in p["devices"])
    tested = "".join(f"<li>{e(x)}</li>" for x in p["tested"])
    plates = "".join(plate(r, page_link=False) for r in rs)
    eyebrow = (f'<a href="videos.html">Videos</a> · <time datetime="{v["date"]:%Y-%m-%d}">{day(v["date"])}</time>'
               f' · {fmt_dur(v["dur"])}')
    return f"""<main id="top">
<div class="wrap">
{page_head(eyebrow, v["title"], extra_cls="vp-head")}
  <div class="vp-grid">
    <div class="vp-main">
      <div class="embed" data-embed="{vid}" data-title="{e(v['title'])}"><a href="{yt(vid)}" target="_blank" rel="noopener">{vthumb(v, big=True)}<span class="visually-hidden">Play {e(v['title'])} on YouTube</span></a></div>
      <div class="vp-intro">{intro}</div>
    </div>
    <aside class="vp-side" aria-label="Chapters and devices">
      <h2 class="subhead-label">Chapters</h2>
      <ol class="chapters">{chapters}</ol>
      <h2 class="subhead-label">On the bench</h2>
      <ul class="jump">{devices}</ul>
    </aside>
  </div>
{section("result", "Result" if len(rs) == 1 else "Results", "", '<div class="plates">' + plates + "</div>", None)}
{section("tested", "What I tested", "", f'<ul class="tested">{tested}</ul>', None)}
  <p class="held">{e(p["note"])} <a class="inline" href="{yt(vid)}" target="_blank" rel="noopener">Watch on YouTube ↗</a></p>
</div>
</main>"""

# ================================================================ assembly
def body(current, main):
    return "\n".join([topbar(current), main, footer(), SCRIPT])

def font_faces(prefix):
    fams = {"Big Shoulders Display": ("big-shoulders-display", (700, 800, 900)),
            "IBM Plex Sans": ("ibm-plex-sans", (400, 500, 600)),
            "IBM Plex Mono": ("ibm-plex-mono", (400, 500, 600))}
    return "\n".join(f'@font-face{{font-family:"{f}";font-style:normal;font-weight:{w};font-display:swap;'
                     f'src:url({prefix}{p}-latin-{w}-normal.woff2) format("woff2")}}'
                     for f, (p, ws) in fams.items() for w in ws)

DESC = ("I test handheld PCs, eGPUs and mini PCs the way I actually use them. Every result comes with its "
        "power limit and run conditions, and I buy everything I review.")

def prod_head(title, path, desc, jsonld=None, og=None):
    url = DOMAIN + path
    ld = f'<script type="application/ld+json">{json.dumps(jsonld, separators=(",", ":"))}</script>\n' if jsonld else ""
    og_img, og_w, og_h, og_alt = og or (DOMAIN + "og-image.png", 1200, 630,
                                        "No_Tech-Dad channel art with the No_Tech-Dad wordmark and tagline")
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{url}">
<meta name="theme-color" content="#121011" media="(prefers-color-scheme: dark)">
<meta name="theme-color" content="#FAF8F8" media="(prefers-color-scheme: light)">
<link rel="icon" href="favicon.ico" sizes="48x48">
<link rel="icon" href="icon-192.png" type="image/png" sizes="192x192">
<link rel="apple-touch-icon" href="apple-touch-icon.png">
<meta property="og:type" content="website">
<meta property="og:site_name" content="No_Tech-Dad">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{og_img}">
<meta property="og:image:width" content="{og_w}">
<meta property="og:image:height" content="{og_h}">
<meta property="og:image:alt" content="{e(og_alt)}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:site" content="@No_TechDad">
<link rel="me" href="{CHANNEL}">
<link rel="me" href="https://x.com/No_TechDad">
<link rel="preload" href="fonts/big-shoulders-display-latin-900-normal.woff2" as="font" type="font/woff2" crossorigin>
{ld}<style>
{font_faces("fonts/")}
{CSS}
</style>
</head>
<body>
"""

def all_pages():
    """(nav key, file, title, description, main html, json-ld, og image) for every page."""
    site_ld = {"@context": "https://schema.org", "@type": "WebSite", "name": "No_Tech-Dad", "url": DOMAIN,
               "description": DESC,
               "publisher": {"@type": "Organization", "name": "No_Tech-Dad", "url": DOMAIN,
                             "logo": DOMAIN + "icon-256.png", "email": EMAIL,
                             "sameAs": [CHANNEL, "https://x.com/No_TechDad"]}}
    pages = [
        ("home", "index.html", "No_Tech-Dad · Handheld PCs, eGPUs and mini PCs, tested", DESC, home_main(), site_ld, None),
        ("videos", "videos.html", "Videos · No_Tech-Dad",
         "Every long-form No_Tech-Dad video on handheld PCs, eGPUs and mini PCs, newest first.", videos_main(), None, None),
        ("results", "results.html", "Results · No_Tech-Dad",
         "Measured results from No_Tech-Dad's videos, each with the conditions it was measured under.", results_main(), None, None),
        ("method", "method.html", "Method · No_Tech-Dad",
         "How No_Tech-Dad tests handheld PCs, eGPUs and mini PCs: capture, power limits, conditions, runs and labels.",
         method_main(), None, None),
        ("bench", "bench.html", "Inventory · No_Tech-Dad",
         "The handheld PCs, graphics cards, eGPUs, docks, displays and filming gear behind No_Tech-Dad's tests.",
         bench_main(), None, None),
        ("news", "news.html", "Industry news · No_Tech-Dad",
         "Handheld PC, graphics and eGPU news, from GPU prices to DLSS and FSR 4, with sources.", news_main(), None, None),
        ("links", "links.html", "Useful links · No_Tech-Dad",
         "The latest AMD, Intel and NVIDIA graphics drivers, handheld makers' support pages, and open-source tools for "
         "handheld gaming PCs.", links_main(), None, None),
        ("about", "about.html", "About · No_Tech-Dad",
         "Nizzel, the dad behind No_Tech-Dad: a problem solver who buys every device and runs every test, supported by AI.",
         about_main(), None, None),
    ]
    for vid, p in VIDEO_PAGES.items():
        v = VBYID[vid]
        r = next((r for r in RESULTS if r["video"] == vid), None)
        desc = r["finding"] if r else BLURBS.get(vid, DESC)
        thumb = f"https://i.ytimg.com/vi/{vid}/maxresdefault.jpg"
        ld = {"@context": "https://schema.org", "@type": "VideoObject", "name": v["title"],
              "description": BLURBS.get(vid, desc), "thumbnailUrl": [thumb], "uploadDate": p["published"],
              "duration": p["iso"], "contentUrl": yt(vid), "embedUrl": f"https://www.youtube-nocookie.com/embed/{vid}"}
        pages.append(("videos", p["file"], f"{v['title']} · No_Tech-Dad", desc, companion_main(vid), ld,
                      (thumb, 1280, 720, v["title"])))
    return pages

SITE_IMAGES = ("badge.png", "nizzel-portrait.jpg", "bench-handhelds.jpg", "bench-desk.jpg", "channel-art.jpg")

def write_preview(pages, out):
    """A copy for previewing outside the live site: Google Fonts instead of the self-hosted ones."""
    out = Path(out)
    if out.exists():
        shutil.rmtree(out)
    (out / "img").mkdir(parents=True)
    for name in SITE_IMAGES:
        shutil.copy(REPO / "img" / name, out / "img" / name)
    for key, fname, title, desc, mhtml, ld, og in pages:
        doc = body(key, mhtml)
        if fname == "index.html":
            (out / fname).write_text(f'<title>No_Tech-Dad</title>\n<meta name="claude:viewport-fit-sides" content="cover">\n'
                                     f"{GF}\n<style>\n{CSS}\n</style>\n{doc}\n")
        else:
            (out / fname).write_text(
                '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
                '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n'
                f'<meta name="claude:viewport-fit-sides" content="cover">\n<title>{e(title)}</title>\n'
                f"{GF}\n<style>\n{CSS}\n</style>\n</head>\n<body>\n{doc}\n</body>\n</html>\n")

ALLOWED_EMAILS = {EMAIL.lower()}
PRIVATE = [  # (pattern, what it means); nothing like this may ever reach the published site
    (r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", "an email address other than the site's"),
    (r"HK\$|AED\s?\d|\bprice paid\b", "a price paid"),
    (r"orderCode|yourpledge|pledges-and-orders", "an order or pledge link"),
]

def check(pages):
    """Fail the build on broken internal links or anything private in the published files."""
    problems = []
    files = {f for _, f, *_ in pages} | {"404.html"}
    ids = {f: set(re.findall(r'\sid="([^"]+)"', (REPO / f).read_text())) for f in files}
    for f in sorted(files):
        text = (REPO / f).read_text()
        for href in re.findall(r'href="([^"]+)"', text):
            if href.startswith(("http", "mailto:", "/")) or href in ("./", "#top"):
                continue
            target, _, frag = href.partition("#")
            target = target or f
            if not (REPO / target).exists():
                problems.append(f"{f}: link to missing file {href}")
            elif frag and target in ids and frag not in ids[target]:
                problems.append(f"{f}: link to missing anchor {href}")
        for pattern, meaning in PRIVATE:
            for m in re.finditer(pattern, text):
                if meaning.startswith("an email") and m.group(0).lower() in ALLOWED_EMAILS:
                    continue
                problems.append(f"{f}: {meaning}: {m.group(0)}")
    return problems

def main():
    pages = all_pages()
    for key, fname, title, desc, mhtml, ld, og in pages:
        path = "" if fname == "index.html" else fname
        (REPO / fname).write_text(prod_head(title, path, desc, ld, og) + body(key, mhtml) + "\n" + counter_tag() + "</body>\n</html>\n")
    (REPO / "CNAME").write_text("notechdad.com\n")
    tokens = CSS[CSS.index(":root{"):CSS.index("*{box-sizing")]
    (REPO / "404.html").write_text(f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Page not found · No_Tech-Dad</title>
<meta name="robots" content="noindex">
<link rel="icon" href="/favicon.ico" sizes="48x48">
<link rel="icon" href="/icon-192.png" type="image/png" sizes="192x192">
<style>
{font_faces("/fonts/")}
{tokens.strip()}
*{{box-sizing:border-box}}
html,body{{height:100%}}
body{{margin:0;background:var(--bg);color:var(--fg);font-family:var(--body);font-size:16px;line-height:1.6;display:grid;place-items:center;padding-left:max(16px, env(safe-area-inset-left, 0px));padding-right:max(16px, env(safe-area-inset-right, 0px))}}
main{{max-width:30rem;padding-block:48px}}
main img{{width:72px;height:72px;display:block}}
.code{{font-family:var(--mono);font-size:12.5px;letter-spacing:.1em;text-transform:uppercase;color:var(--red-ink);margin:24px 0 8px}}
h1{{font-family:var(--display);font-weight:900;font-size:clamp(48px,12vw,84px);line-height:.9;text-transform:uppercase;margin:0}}
p{{color:var(--fg-2)}}
a{{display:inline-flex;margin-top:12px;padding:11px 18px;border-radius:4px;background:var(--red-btn);color:var(--on-red);font-weight:600;text-decoration:none}}
a:focus-visible{{outline:2px solid var(--gold);outline-offset:3px}}
</style>
</head>
<body>
<main>
<img src="/img/badge.png" width="72" height="72" alt="">
<p class="code">Error 404 · page not found</p>
<h1>Nothing on this bench</h1>
<p>The page you asked for doesn't exist, or it moved.</p>
<a href="/">Back to notechdad.com</a>
</main>
</body>
</html>
""")
    urls = "".join(f"  <url><loc>{DOMAIN}{'' if f == 'index.html' else f}</loc><lastmod>{SITEMAP_DATE}</lastmod></url>\n"
                   for _, f, *_ in pages)
    (REPO / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n'
                                      '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + urls + "</urlset>\n")
    if ARGS.preview:
        write_preview(pages, ARGS.preview)
    print("pages:", ", ".join(f for _, f, *_ in pages))
    print("on bench:", ON_BENCH, "| videos:", len(VIDEOS), "| newest:", VIDEOS[0]["id"], "| results:", len(RESULTS),
          "| links:", links_count())
    problems = check(pages)
    if problems:
        print("CHECKS FAILED, do not publish:\n  " + "\n  ".join(problems))
        sys.exit(1)
    print("checks passed: internal links resolve, nothing private in the published pages")

main()
