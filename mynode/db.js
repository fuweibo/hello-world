const Sequelize = require('sequelize');

module.exports = new Sequelize('blog','root','root',{
    host : 'localhost',
    dialect : 'mysql',
    poll : {
       max : 5,
       min : 0,
       idle : 10000
    }
});
