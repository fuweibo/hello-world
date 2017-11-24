//koa框架加载
const Koa = require('koa');
//路由模块加载
const Router = require('koa-router');
//加载模板引擎模块
const views = require('koa-views');
//加载path模块
const path = require('path');
//导入user.js
const User = require('./user')

//加载静态文件
const serve = require('koa-static')
const convert = require('koa-convert')

// 跨域
const cors = require('koa-cors')

// body解析
const bodyParser = require('koa-bodyparser')

const app = new Koa();
const router = new Router();

app.use(convert(cors({ origin: '*' })))
app.use(convert(bodyParser({ limit: '10mb' })))

async function main(){
/*
koa-views 通过 views(__dirname + '/views', 指定了模板文件所在的目录 - 根目录下的 views 文件夹；
通过 { map: { jade: 'jade', html: 'mustache' } } 指定使用 jade 模板引擎解析 .jade 文件，
使用 mustache 模板引擎解析 .html 文件。
*/
app.use(views(path.join(__dirname + '/public'),{
   map : { jade : 'jade',html : 'mustache' }
}));

//加载静态文件
app.use(convert(serve(path.join(__dirname, './public'))))

/*
//服务器发送jade文件给前台
router.get('/',async (ctx,next) =>{
   await ctx.render('index.jade',{ pageTitle : '首页' });
});

//服务器发送html页面给前台
router.get('/app', async (ctx , next) => {
   await ctx.render('app.html' , { pageTitle : '控制台' });
});
*/

//首页
router.get('/',async (ctx,next)=> {
   await ctx.render('index.html',{ pageTitle : '首页'}); //通过ajax请求过来的话，是不会跳转的
});

//注册
router.get('/regist', async (ctx,next)=> {
   let res = await User.addUser(ctx.query.username,ctx.query.password);
   console.log(JSON.stringify(res));
   //ctx.body = `successCallback(${JSON.stringify(res)})` //实现跨域后，能进入success的条件
   ctx.body = res
});

//登录
router.post('/login', async (ctx , next) => {
    let {username , password} = ctx.request.body;
    let res = await User.selectUser(username,password);
    console.log(res);
    if(res){
        //await ctx.redirect('app.html');
        await ctx.render('app.html' , { pageTitle : '控制台' });
    }
})

//在router上面注册一个监听服务端根目录的get请求
router.get('/test',(ctx,next)=>{
   ctx.body = 'Hello,World!'
});

//加载路由
await app.use(router.routes());

app.listen(3000);
console.log('Koa started on port 3000');
}
main();
