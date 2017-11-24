//user.js

var Sequelize = require('sequelize');
var sequelize = require('./db');

//创建model
var User = sequelize.define('user',{
   username : {
      type : Sequelize.STRING,  //指定值的类型
      //field : 'user_name' //指定存储在表中的键名称
   },
   //没有指定field，表中键名称则与对象键名相同，为email
   password : {
      type : Sequelize.STRING
   }
},{
   // 如果为 true 则表的名称和 model 相同，即 user 
   // 为 false MySQL 创建的表名称会是复数 users 
   // 如果指定的表名称本就是复数形式则不变
   freezeTableName : true
});


//创建表
//var user = User.sync({force : false});

//添加用户
exports.addUser = function(username,password) {
	//向user表中插入数据
	return User.create({
		username : username,
		password : password
});
};

//根据用户名查找用户
exports.selectUser =async function(username,password){
    let res =await User.findOne({where : {username : username , password : password}});
	return res ? res.get() : undefined;
};
