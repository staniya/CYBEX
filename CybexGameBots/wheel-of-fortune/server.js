var express = require('express');
var app = express();

app.use(express.static('static'));

app.get('/', function (req, res) {
   res.sendFile(__dirname + "/" + "index.html");
})
 
var server = app.listen(8080, function () {
 
  var host = server.address().address
  var port = server.address().port
 
  console.log("Instance: http://%s:%s", host, port)
 
})
