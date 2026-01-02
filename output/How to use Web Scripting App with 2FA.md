# How to use Web Scripting App with 2FA

If your dashboard requires login with the 2FA, OptiSigns supports the 2FA in the Web Scripting app.

If your dashboard doesn't require the 2FA, you can just follow this [article](https://support.optisigns.com/hc/en-us/articles/1500012522362).

## **Let's jump in and get started:**

1. Will need the get the **Secret key**:\
Before you set up the 2FA with the QR code, you can click "cannot see the QR". It will provide you with a Secret key. You can copy that key.\
Here is an example:

![](/attachments/token/xOjvcQdIqA9avnfjpzeOZVRqG/?name=image.png)

You can get the Secret key:

![](/attachments/token/0MBnE1wGrWf20KsUlRNDpncuK/?name=image.png)

After that, click the Scan a QR code. Finish 2FA setup.\
\
2. Then you can use the **Burp Suite Navigation Recorder**to record the script.\
[How to use Web Scripting App – OptiSigns](https://support.optisigns.com/hc/en-us/articles/1500012522362-How-to-use-Web-Scripting-App)\
\
3. You can copy the script in the Web Scripting app.

![](/attachments/token/0XtC76qd4uFdnNZ9xFev0SlJB/?name=image.png)

* **Secret 2FA:**Thiswill be the Secret key when you set up the 2FA.
* **Recorded 2FA Code:**This will be the one that you enter the code when you do the script recording.

If you have any additional questions, concerns, or any feedback about OptiSigns, feel free to reach out to our support team at [support@optisigns.com](mailto:support@optisigns.com)