# Amazon TV / FireStick Troubleshooting Guide

If you are experiencing black screens, device not powering up, not connected to network, etc.

Please follow the steps below for troubleshooting, it commonly resolve 90%+ of the issues.

|  |
| --- |
| **IMPORTANT** |
| In 2024, [Amazon released an update to FireOS](https://www.aftvnews.com/amazon-blocks-long-running-fire-tv-capability-breaking-popular-apps-with-no-warning-and-giving-developers-the-runaround/) disallowing apps to be autostarted on device boot up. Amazon has also released a [Digital Signage Stick](https://www.amazon.com/Amazon-Signage-Stick-quad-core-streaming/dp/B0D4FCG9MX?dib=eyJ2IjoiMSJ9.Q2R-IsQqpFLBQnyOzroJsCqvInA20YBPOGzYxBJPkImYB91-GaLrO5UB3QrtLmJNwXLsi1fcGV1xu_Zl1s8COTf9QMkHac5UyzG7eQagHUewWSm6EEX6Ef0TmSwamrXclpPnL6J1v88a_qtAqCQKpVuNT5XuDAY3Qpa6PdiPg7wjiwccWWmcqndZNHXRGySXbmZWq_btwj6lEz6wMm8nGy9OZwFNRh1bLYrx9luXUOk.BITMseiknoYwYECYPBkXIneqN89ySUCEo8SujSNiprA&dib_tag=se&keywords=Digital+Signage+Player&qid=1751559195&sr=8-4&ufe=app_do%3Aamzn1.fos.74097168-0c10-4b8a-b96b-8388a1a12daf) to replace the FireStick as a digital signage option. [Amazon is also pushing advertising services,](https://www.theverge.com/2023/12/1/23984444/amazon-fire-tv-autoplay-ads-on-startup) so device playback may be randomly interrupted.  On top of this, the newest models of the Amazon FireTV/FireStick (ex. 4K Select) run on VegaOS, and are totally unsupported by OptiSigns as of early 2026.  For these reasons, we no longer recommend FireStick as a digital signage player. We recommend an Amazon Signage Stick, Windows or Linux device, Chromecast, or our [Android Player Stick](https://shop.optisigns.com/products/optisigns-android-stick-player-2). |

**VegaOS (2025+): Device Incompatible**

OptiSigns is not currently supported on VegaOS Amazon FireSticks and cannot be downloaded.

**FireOS 8 (2023-2025) Model autostart:**

If you already have a newer model and still want to try to use it, and you can handle ADB via USB commands, [please follow this guide to enable](https://support.optisigns.com/hc/en-us/articles/23274673797139-How-to-enable-auto-start-on-the-Amazon-Fire-TV-Stick-4K-Gen-2s-2023-model) ADB and autostart for your device.

**Networking: (This is the most common issue)**

* This test will resolve most of the networking issues:
  + Try mobile hotspot
  + Try different network (bring the device home or to another location)
* Other networking check:
  + Check internet connection - open side menu -> Troubleshooting. Check see if device is connected to our servers. Without connection device cannot receive files, content updates
    - [Reference of the Troubleshooting page of the OptiSigns app](https://support.optisigns.com/hc/en-us/articles/36501302096915)
  + If you have firewalls, make sure our [servers are whitelisted.](https://support.optisigns.com/hc/en-us/articles/360047275934-Whitelist-OptiSigns-IP-addresses-ports)

**Performance, Freezing:**

* FireStick and FireTVs are best with 3-4 zones without background music (or 2 zones with background music). If you more zones than that, you may experience instability.

**Check power cables & connections:**

* One of the most common causes of device stability is not using provided power adapters & cables. TV’s USB ports do not have sufficient power to stably run the device for extended periods of time

**HDMI & TV connection:**

* Try a different HDMI port on your TV
* Try to connect device directly to TV without HDMI extender
* Try a different TV, Monitor

**Device is on, but start playing black screen:**

* Check to make sure Device is not in [OnHold folder](https://app.optisigns.com/app/screenManagement?path=~2FOnhold%20Device&teamId=1) - sometimes you may not have enough licenses on your account when ordering devices so your device is in the OnHold folder.
  + Remove unused device or increase your subscription and move your device out of OnHold
* Check make sure there is playlist or other content assigned to your screen

**Remote Controller issues:**

* Ensure batteries are installed in remote controller, try fresh batteries.
* [Use your phone as FireTV/Stick remote](https://www.lifewire.com/use-phone-as-remote-control-for-amazon-fire-tv-stick-4571277)

**Factory Reset:**

Lastly, you can try [Factory Reset the device](https://support.optisigns.com/hc/en-us/articles/360054298754-How-to-Factory-Reset-Your-Fire-Stick-device).