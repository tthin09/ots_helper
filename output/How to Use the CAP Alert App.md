# How to Use the CAP Alert App

### In this article, we will show you how to set up and test the CAP Alert app in OptiSigns.

* [How to Set Up a CAP Alert App](#Set)
* [How to Test Your CAP Alert](#Test)

|  |
| --- |
| **NOTE** |
| The CAP Alert app is available to **Pro Plus** subscribers and above. |

Some Emergency Alert Systems or Emergency Mass Notification Systems (like Everbridge, RAVE. and Alertus) can push CAP (Common Alerting Protocol) and Integrated Public Alert and Warning System (IPAWS) messages to the targets including digital signage when there is an emergency. You can integrate with these systems using the CAP Alert app with OptiSigns.

Using OptiSigns' CAP Alert app, you can generate a webhook and integrate it with the Emergency Alert System. When there is an emergency, the emergency alert system will call the webhook to send the CAP/IPAWS message and trigger the CAP alert app. The CAP/IPAWS alert will take over the target screens and display the emergency message. The screen will resume and play the original content when the emergency is over.

![example of CAP alert with emergency text](https://support.optisigns.com/hc/article_attachments/6605782051731)

---

## How to Set Up a CAP Alert App

First, you will need to have your screens set up and paired. For more information on how to do that, see our article on [How to Set Up Digital Signs with OptiSigns](https://www.optisigns.com/blog/how-to-set-up-digital-signs-with-optisigns-and-amazon-fire-tv).

Then log on to our portal: <http://app.optisigns.com/>

Go to **Files/Assets**, Click on "App"

![optisigns web browser with arrows pointing at files/assets tab and app button](https://support.optisigns.com/hc/article_attachments/29815731038611)Select "CAP Alert" app:![optisigns web browsers showing the cap alert app](https://support.optisigns.com/hc/article_attachments/29815756561555) Set up your CAP alert app:![cap alert app setup window in optisigns web browser](https://support.optisigns.com/hc/article_attachments/33695686409235)

* **Name** - Name of your assets, this will not be displayed on the screens.
* **Target** - Select Screens or Tags.
* **Screens/Tags** - Select which screens or group of screens (tags) you want to target for this emergency. (i.e. Fire in building/location 1)
* **Content-Type** - Select "Post to Webhook" if you would like to post the CAP/IPAWS message to your signage. The app also supports RSS feed.
* **Webhook** - The app will generate a webhook URL after it is saved. This is what you should share with the emergency alert system.
* **Display Type** - Currently the app will take over the full screen when there is an emergency
* **State**- Set the app to active or inactive.
* **Emergency Duration**- How long the emergency message will take over the screen. The value can be overwritten by the webhook call.

**Advanced settings:**

![advanced settings of cap alert app in optisigns web browser](https://support.optisigns.com/hc/article_attachments/33695707675411)

* **Using Text Font, Color, Background Color, Text Alignment, and Background Image** - Allows you to design the message as you desire (i.e. text shows up in the middle of the screen on top of your organization's branded image template)
* **Item Duration** - How long each individual item in the RSS feed will display.
* **Title Tag** - Message title from the CAP/IPAWS message/RSS feed, default is <headline> - you can change if your feed is different
* **Description Tag** - Message content from the CAP/IPAWS message/RSS feed, default is <description> - you can change if your feed is different
* **Location (Screen Tags)** - If you can match the screen tags with your location passed from the CAP/IPAWS message/RSS feed - you can use it to control the selection of the target screens. By default, it maps to the "areaDesc" attribute from the CAP alert.

|  |
| --- |
| **IMPORTANT** |
| A common issue we find is the screen displays a "No Content Available" message after users push out the CAP alert using "aeraDesc" an attribute. The solution: if you are not intending to use screen tags to map to location, try changing the Location value from "areaDesc" to any other value, like "areaDesc2". |

* **Filter content containing** - Allows content to be filtered based on specific words in the title or description. I.E: "fire", so if any title or description contains the word "fire" (non-case insensitive), the app will trigger the screen takeover.
* **Exclude title containing** - Filter only applying to the title. You can hide all the old feeds by filtering with specific words in the title. I.E: “All Clear”, so after the emergency is gone, all the feeds before this title will be hidden, then the screen will revert to the original content or just display the new content after that.
* **Use Urgency, Severity, Certainty, and Status to control the filter of the CAP messages**, these are standard attributes of CAP/IPAWS messages. By default, the app will be triggered on all values. Once selected, they can be set similar to tags:

![demonstration of urgency, severity, certainty, status options using tags](https://support.optisigns.com/hc/article_attachments/33695707683987)

Selected choices will continue to appear.

When finished, click **Save**.

---

## How to Test Your CAP Alert

After Saving, the app will generate a Webhook URL automatically. When this Webhook is called, it will perform the functions designated in your CAP Alert app. If you share the Webhook URL with your Emergency Alert System, it will be able to trigger this Webhook during an emergency and take over the screens.\
\
To test your CAP alert integration, we recommend using [Postman](https://www.postman.com/) to post a CAP/IPAWS message to the Webhook.First, download or log in to Postman. Once there, navigate to **Home → Send an API request → New Request:****![postman with arrows pointing toward Home tab and New Request button](https://support.optisigns.com/hc/article_attachments/33695686427411)**Once here, change the request type to **POST:**![postman demonstration of how to select POST option](https://support.optisigns.com/hc/article_attachments/33695686435475)Input the Webhook URL for your CAP Alert next.Now, navigate to the **Body** tab. Here, you can send data two ways: **URL encoded** or as a **raw XML file**. Here we will assume you are sending your data as raw XML, as this is the most common format we see from Emergency Alert Services.CAP/IPAWS Alerts are generally delivered via an external Emergency Alert System, which are saved as **.xml** or **.txt** files. These are broadcast via the [Common Alerting Protocol Version 1.2](https://docs.oasis-open.org/emergency/cap/v1.2/CAP-v1.2-os.html). To push an XML file, click the **raw → Dropdown →** select **XML**.**![postman step by step on selecting XML format](https://support.optisigns.com/hc/article_attachments/33695686448403)**Then, copy and paste the following piece of test code into the field:

```
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\
<alert xmlns="urn:oasis:names:tc:emergency:cap:1.2">\
    <identifier>ALERTUS_2317_67_20230131_162046</identifier>\
    <sender>Tester</sender>\
    <sent>2023-01-31T11:20:47-05:00</sent>\
    <status>Actual</status>\
    <msgType>Alert</msgType>\
    <source>Alertus eEAS Server</source>\
    <scope>Public</scope>\
    <addresses>ALL</addresses>\
    <code>IPAWSv1.0</code>\
    <info>\
        <language>en-US</language>\
        <category>Safety</category>\
        <event>TEST Event Name Override</event>\
        <responseType>None</responseType>\
        <urgency>Immediate</urgency>\
        <severity>Severe</severity>\
        <certainty>Observed</certainty>\
        <eventCode>\
            <valueName>SAME</valueName>\
            <value>LAE</value>\
        </eventCode>\
        <effective>2023-01-31T11:20:47-05:00</effective>\
        <onset>2023-01-31T11:20:47-05:00</onset>\
        <expires>2023-01-31T11:23:46-05:00</expires>\
        <headline>Test286</headline>\
        <description>This is a Test of the Alertus Emergency Notification System. NO ACTION is Needed. In a real emergency, this system will be used to provide emergency information and protective actions. Please return to your normal activities.</description>\
        <area>\
            <areaDesc1>Tag1</areaDesc1>\
            <geocode>\
                <valueName>SAME</valueName>\
                <value>000000</value>\
            </geocode>\
        </area>\
        <parameter> \
            <valueName>duration</valueName> \
            <value>30</value> \
        </parameter> \
    </info>\
</alert>
```

It will look something like this:

![postman xml input example](https://support.optisigns.com/hc/article_attachments/33695707719699)

You can set the duration of the CAP/IPAWS alert message as well. In raw XML format, you can pass the duration value through a system parameter in your CAP alert message.

Now, to test the request, hit **Send**. A piece of text should appear on the console below. If the test was successful, it should give a **200 OK code** and say "status": "success":

![postman showing code layout under raw data tab](https://support.optisigns.com/hc/article_attachments/33695707725715)

And this message (assuming all the defaults were kept in the CAP Alert app) will appear on your screen:

![test message for the CAP alert system](https://support.optisigns.com/hc/article_attachments/33695707733779)

#### Creating a Test Request in urlEncoded Format

Using urlEncoded format, the duration can be passed as URL parameter together with data.

![example in postman of urlencoded format](https://support.optisigns.com/hc/article_attachments/33696696479251)

The rest of the test can be performed identically.

### That's all!

If you have any additional questions, concerns or any feedback about OptiSigns, feel free to reach out to our support team at [support@optisigns.com](mailto:support@optisigns.com)