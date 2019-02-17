# judge

* Google clouds app engine that judges an online article (given its URL) based on its positivity/ngativity and its respective magnitude
* Still TODO: map magnitude to "bias"
* Instructions to run:
  * open Google Cloud Platform
  * click Activate Cloud Shell icon in upper right 
  * click Launch Code Editor
  * copy past all the files and directories into the project
  * enter the following in the console: gcloud app deploy
  * after it is running, go to the link: https://treehacksproj.appspot.com/form
  * enter random name, email and comment, but make sure you enter desired URL for example: https://www.cnn.com/2019/02/16/middleeast/syria-isis-caliphate-sdf-intl/index.html
  * click the submit button
  * outputs a metric describing the document's tone: 
   * no emotions
   * little emotions
   * medium emotions
   * high emotions
