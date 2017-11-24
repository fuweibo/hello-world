//user.js


var Sequelize = require('sequelize');
var sequelize = require('./db');

//创建model
var User = sequelize.define('user',{
   userName : { 
      type : Sequelize.STRING,  //指定值的类型
      //field : 'user_name' //指定存储在表中的键名称
   },       
   //没有指定field，表中键名称则与对象键名相同，为email
   email : { 
      type : Sequelize.STRING
   }  
},{
   // 如果为 true 则表的名称和 model 相同，即 user 
   // 为 false MySQL 创建的表名称会是复数 users 
   // 如果指定的表名称本就是复数形式则不变
   freezeTableName : true
}); 
    
//创建表
// User.sync() 会创建表并且返回一个 Promise 对象
// 如果 force = true 则会把存在的表（如果 users 表已存在）先销毁再创建表
// 默认情况下 forse = false
var user = User.sync({force : false});


//添加新用户
exports.addUser = function(userName,email) {
   //向user表中插入数据
   return User.create({
      userName : userName,
      email : email
   })
};

//通过用户名查找用户
exports.findByName = function(userName) {
   return sequelize.model('user').findOne({where : {userName : userName}});
};


