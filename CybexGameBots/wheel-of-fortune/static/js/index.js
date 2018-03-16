var app = app || {};

new WOW().init()

app = (function() {
  'use strict';
  
  var wheel = function() {

    // set up all our vars which are shared across functions

    var containerEl = document.getElementById('container'),

    wedgeColors = [
      '#F44336',
      '#F02F4E',
      '#E91E63',
      '#CB2392',
      '#9C27B0',
      '#673AB7',
      '#5446B6',
      '#3F51B5',
      '#2C63C3',
      '#1976D2',
      '#448AFF',
      '#03A9F4',
      '#00BCD4',
      '#00D8DB',
      '#009688',
      '#4CAF50',
      '#8BC34A',
      '#CDDC39',
      '#FFEB3B',
      '#FFC107',
      '#FF9800',
      '#FF5722'
    ],

    numOfWedges = 22,
    wheelRadius = 230,
    maxAngularVelocity = 360 * 1.5,
    angularFriction = 0.75,
    angularVelocity = 360,
    lastRotation = 0,
    controlled = false, // set true for no autospin

    target,
    activeWedge,
    stage,
    layer,
    wheel,
    pointer,
    pointerTween,
    startRotation,
    startX,
    startY;


    // used for randomizing the colour array
    // Fisher-Yates (aka Knuth) Shuffle

    // now we shuffle the color array

    function addWedge(n) {
      
      var angle = 360 / numOfWedges;

      var wedge = new Kinetic.Group({
        rotation: n * 360 / numOfWedges,
      });


      var wedgeBackground = new Kinetic.Wedge({
        radius: wheelRadius,
        angle: angle,
        fill: wedgeColors.pop(),
        //stroke: '#fff',
        //strokeWidth: 2,
        rotation: (90 + angle/2) * -1
      });

      wedge.add(wedgeBackground);

      var text = new Kinetic.Text({
        text: '福',
        font-family: 'Hiragino Kaku Gothic Pro', 'WenQuanYi Zen Hei', '微軟正黑體', '蘋果儷中黑', Helvetica, Arial, sans-serif;  letter-spacing: -1px;
        fontSize: 30,
        fill: '#fff',
        align: 'center',
        //stroke: '#fff',
        //strokeWidth: 2,
        opacity: 0.95,
        listening: false

      });
      
      text.offsetX(text.width()/2);
      text.offsetY(wheelRadius - 15);
      
      wedge.add(text);
      wheel.add(wedge);

    }

    function animate(frame) {
      // wheel
      var angularVelocityChange = angularVelocity * frame.timeDiff * (1 - angularFriction) / 1000;
      angularVelocity -= angularVelocityChange;

      wheel.rotate(frame.timeDiff * angularVelocity / 1500);
      
      lastRotation = wheel.getRotation();

      // pointer
      var intersectedWedge = layer.getIntersection({
        x: stage.width()/2, 
        y: 50
      });
      
      if (intersectedWedge && (!activeWedge || activeWedge._id !== intersectedWedge._id)) {
        pointerTween.reset();
        pointerTween.play();
        activeWedge = intersectedWedge; 
        
       //$('#winner').text(activeWedge.parent.children[1].partialText);

      }
    }

    function init() {
      stage = new Kinetic.Stage({
        container: 'container',
        width: wheelRadius * 2,
        height: wheelRadius * 2 + 20 // plus 20 is for the pointer
      });
      layer = new Kinetic.Layer();
      wheel = new Kinetic.Group({
        x: stage.getWidth() / 2 ,
        y: wheelRadius + 20
      });

      for (var n = 0; n < numOfWedges; n++) {
        addWedge(n);
      }
      
      pointer = new Kinetic.Wedge({
        fill: '#dedede',
        //stroke: '#fff',
        //strokeWidth: 0,
        lineJoin: 'round',
        angle: 35,
        radius: 20,
        x: stage.getWidth() / 2,
        y: 22,
        rotation: -105
      });

      // add components to the stage
      layer.add(wheel);
      layer.add(pointer);
      stage.add(layer);
      
      pointerTween = new Kinetic.Tween({
        node: pointer,
        duration: 0.1,
        easing: Kinetic.Easings.EaseInOut,
        y: 30
      });
      
      pointerTween.finish();
      
      var radiusPlus2 = wheelRadius + 2;
      
      /*wheel.cache({
        x: -1* radiusPlus2,
        y: -1* radiusPlus2,
        width: radiusPlus2 * 2,
        height: radiusPlus2 * 2
      }).offset({
        x: radiusPlus2,
        y: radiusPlus2
      });*/
      
      layer.draw();


      // Time to start adding the event listeners
      
      function handleMovement() {

        var touchPosition = stage.getPointerPosition(),
            x1 = touchPosition.x - wheel.x(),
            y1 = touchPosition.y - wheel.y();         
      
        if (controlled && target) {

          var x2 = startX - wheel.x(),
              y2 = startY - wheel.y(),
              angle1 = Math.atan(y1 / x1) * 180 / Math.PI,
              angle2 = Math.atan(y2 / x2) * 180 / Math.PI,
              angleDiff = angle2 - angle1;
          
          if ((x1 < 0 && x2 >=0) || (x2 < 0 && x1 >=0)) {
            angleDiff += 180;
          }

          wheel.setRotation(startRotation - angleDiff);

        }
      };

      var button_my_button = ".reset-btn";
      $(button_my_button).click(function(){
        var anim = new Kinetic.Animation(animate, layer);
      //document.getElementById('debug').appendChild(layer.hitCanvas._canvas);
        anim.start();

        var fortune_array = ['利是','大胆尝试', '财运上升', '福至心灵', '坚定', '等待机会', '以静制动', '果断', '平稳', '咸鱼翻身', '逢凶化吉', '选择', '顺遂', '贵人', '十倍币', '百倍币', '信念', '横财', '偏财', '稳步上升', '躺赚'];
        var rand = fortune_array[Math.floor(Math.random() * fortune_array.length)];
      
      });  
    }

    init();
    containerEl.className = 'visible';
    
  }

  return {
    wheel: wheel
  };


})();


window.onload = function() {
    'use strict';

	app.wheel();
	
};