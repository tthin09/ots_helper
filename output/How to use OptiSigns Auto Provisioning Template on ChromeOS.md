# How to use OptiSigns Auto Provisioning Template on ChromeOS

ChromeOS is a popular platform for digital signage with its excellent performance and ease of device management. Google's new Kiosk & Signage Upgrade license for Chrome device management, makes ChromeOS a more competitive option in the digital signage space.

OptiSigns supports Auto Provisioning on ChromeOS, your digital signage deployment using ChromeOS can be fully automated by utilizing our auto-provisioning template. The auto-provisioning process can get the device paired to your account automatically.

If you are new to the ChromeOS deployment, you can read [here](https://support.optisigns.com/hc/en-us/articles/360054033374) first to see how to deploy the OptiSigns application on ChromeOS with Chrome Device Management. This document will follow the provisioning of OptiSigns application(section 1 of the above-mentioned document) and walk you through how to use an auto-provisioning template for Chrome to get the device automatically paired to your account.

## **Let's jump in and get started:**

**1) Create an auto-provisioning template for your Chrome deployment**

To create a provisioning template, you can either access it from the admin menu or use the below link.

<https://app.optisigns.com/app/s/provisioning-templates>

Create a new provisioning template by clicking the "Create templates" button.

![mceclip0.png](https://support.optisigns.com/hc/article_attachments/17360386666771)

Then set the template in the popup.

![mceclip1.png](https://support.optisigns.com/hc/article_attachments/17360357432467)

* Template Name: Name of your template, this is for you to distinguish it when you have multiple provisioning templates.
* Device Name Prefix: This is used to generate the device name during provisioning.
* Device Name Suffix: This is used to generate the device name during provisioning, the default setting will add timestamps as a suffix.
* Folder: The folder you want to have the provisioned devices to be created.
* WIFI: Select from the stored WIFI, need to be created first. Only required if you want to setup WIFI during provisioning. WIFI setup is normally not needed for ChromeOS deployment. Because the deployment will be managed through Chrome Device Management.
* Time Zone: Specify the time zone of the device.
* Tags: Specify the tags you want to associate to the devices.
* Initial Default Content Type: Used to set the initial content on the device after provisioning.
* Orientation: Set the orientation, landscape is the default.
* Sync Play: Used to set the turn on/off of the sync play feature. For more details of Sync Play feature, please click [here](https://support.optisigns.com/hc/en-us/articles/4412065189267-Synchronized-playback-Sync-Play-feature).
* Location: Set the location of the device.

Once the template is created, it will be available under the list of provisioning templates, you can download the config file and it will be used later during deployment. Please make sure to select "ChromeOS" when you click the download button. The configuration file's name is "provisionting-template-<Your Template Name>.txt"

![](https://support.optisigns.com/hc/article_attachments/17359692661139)The file will contain a JSON object, this is what is needed later when setting up auto provisioning on Google Chrome Device Management.![](https://support.optisigns.com/hc/article_attachments/17359871365139)**2) Create mass provisioning template for your Chrome deployment**

OptiSigns uses policy extensions on ChromeOS to provision the device into your account.

Please follow section 1 of this document([how to deploy OptiSigns on ChromeOS with Chrome Device Management](https://support.optisigns.com/hc/en-us/articles/360054033374)) to complete the auto provisioning of the OptiSigns application on your ChromeOS device.

Then go to "Apps&extensions" from Chrome Device Management, find the OptiSigns app from the Kiosks setting.

Find the "Policy for extensions", this is where you put the JSON object from the auto provisioning template file generated above.

![](https://support.optisigns.com/hc/article_attachments/17360066112659)

Save it, then you are ready to start your deployment.

You just need to follow the normal deployment procedure to deploy your ChromeOS device. At the time of deployment, OptiSigns application will be auto installed on your ChromeOS device, then OptiSigns application will check the extension policy, if auto provisioning template is found, OptiSigns application will automatically pair the device to your account and assign the content that was defined in the template.

**That's all!**

If you have any additional questions, concerns or any feedback about OptiSigns, feel free to reach out to our support team at [support@optisigns.com](mailto:support@optisigns.com)