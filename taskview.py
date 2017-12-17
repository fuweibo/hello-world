from flask import request, g, current_app, abort, jsonify
from flask_login import login_required

import os
import json
import uuid
import datetime
import time
import logging
from .. import user_blueprint as blueprint
from ..forms import TaskTypeForm, AddTaskForm, SelectTaskDetails, \
    AddBookArrangementTask, ReviewOneTask, GetAllUncheckedTask, GetArea
from app.models import User, UsersExt, TaskType, Task, Area
from app import current_minio

logger = logging.getLogger("app")


@blueprint.route("/addTaskType", methods=["GET"])
@login_required
def add_task_type():
    """
    params: name //工作类型
    #添加工作类型
    """
    if g.jwt["permission"] not in ["manager", "admin"]:
            return abort(400, "Lack of user rights!!")

    form = TaskTypeForm(request.args)
    if not form.validate():
        return abort(400, "invalid params")
    task_type_name = form.data['name']

    try:
        types = TaskType.get(TaskType.name == task_type_name)
    except Exception as err:
        logging.getLogger("app").debug("types is null: %s", err)
        TaskType.create(uuid=uuid.uuid4(), name=task_type_name)
        return jsonify(state=0, msg="添加成功")

    if types.name is not None:
        return jsonify(state=1, msg="该工作类型已存在！！")


@blueprint.route("/selectAllTaskType", methods=['GET'])
@login_required
def select_all_task_type():
    """
    params: None
    #查找所有工作类型
    """
    if g.jwt["permission"] not in ["manager", "admin"]:
            return abort(400, "Lack of user rights!!")

    task_type = TaskType.select(TaskType.name).limit(7)
    tk_type = [types.name for types in task_type]

    if len(tk_type) == 0:
        return jsonify(state=1, msg="没有任务列表，请先添加！")
    return jsonify(state=0, msg=tk_type)


@blueprint.route("/addTaskToUser", methods=['POST'])
@login_required
def add_task_to_user():
    """
    params: username //用户名, task //工作类型和时间的json
    经理指派日常任务
    任务类型，员工id, 时间，
    """
    if g.jwt["permission"] not in ["manager"]:
            return abort(400, "Lack of user rights!!")

    form = AddTaskForm(request.form)
    if not form.validate():
        return abort(400, "invalid params")

    try:
        json.loads(request.form['task'])
    except:
        return abort(400, "task is not json format")

    task = (UsersExt.select()
            .join(User).where(User.username == form.data['username']).get())
    task_json = request.form['task']
    UsersExt.update(audit=task.userid.leader, last_audit=g.jwt["uuid"], task=json.dumps(task_json))\
        .where(UsersExt.userid == task.userid).execute()
    return jsonify(state=0, msg="ok")


@blueprint.route("/selectUserAllDayTask", methods=["GET"])
@login_required
def select_user_all_day_task():
    """
    params: None
    # 员工查看日常任务
    # 获取员工的id
    :return:
    """
    user_id = g.jwt["uuid"]
    try:
        users = UsersExt.get(UsersExt.userid == user_id)
    except Exception as err:
        logging.getLogger("app").debug("users is null: %s", err)
        return jsonify(state=1, msg="没有日常任务")
    user_task_type = {'task': users.task}
    return jsonify(state=0, msg=user_task_type, dt_task="daily")


@blueprint.route("/addBookArrangementTask", methods=["POST"])
@login_required
def add_book_arrangement_task():
    """
    params:
    # 员工提交图书整理任务
    上传文件
    :return: img
    """
    img = upload_head_img()

    args = dict(request.form)
    form = AddBookArrangementTask(request.form)
    if not form.validate():
        return abort(400, "invalid params")

    area_count, task_type, bk_type, code, message, error_reason, downtime = None, None, None, None, None, None, None
    employee_id = g.jwt["uuid"]
    user = User.get(User.uuid == employee_id)
    user_ext = UsersExt.get(UsersExt.userid == employee_id)
    assignor_id, dt_task = form.data['assignor_id'], form.data['dt_task']
    manager, department_id = user_ext.lastaudit, user.department

    if form.data['tasktype'] == "图书整理":
        task_type = "图书整理"
        area_count = {"res1": request.form['area_count']}
    if form.data['tasktype'] == "倒架统计":
        task_type = "倒架统计"
        message = args['message'][0]
        area_count = {"res1": request.form['area_count']}
    if form.data['tasktype'] == "图书回架":
        task_type = "图书回架"
        bk_type = request.form['bk_type']
        area_count = request.form['area_count']
    if form.data['tasktype'] == "图书盘点":
        task_type = "图书盘点"
        area_count = request.form['area_count']
    if form.data['tasktype'] == "错架率抽样":
        task_type = "错架率抽样"
        area_count = request.form['area_count']
        code = request.form['code']
    if form.data['tasktype'] == "分拣系统":
        task_type = "分拣系统"
        """故障类型"""
        bk_type = request.form['bk_type']
        """故障原因"""
        error_reason = request.form['error_reason']
        """文字描述"""
        message = request.form['message']
        if bk_type == "停机":
            downtime = request.form['downtime']

    if task_type in ["图书盘点", "图书整理"]:
        Task.create(employee=employee_id, supervisor=assignor_id,
                    department=department_id, manager=manager, tasktype=task_type,
                    dt_task=dt_task, area_count=json.dumps(area_count), img_url=img[:-1])
    if task_type in ["倒架统计"]:
        Task.create(employee=employee_id, supervisor=assignor_id, message=message,
                    department=department_id, manager=manager, tasktype=task_type,
                    dt_task=dt_task, area_count=json.dumps(area_count), img_url=img[:-1])
    if task_type in ["图书回架"]:
        Task.create(employee=employee_id, supervisor=assignor_id, bk_type=bk_type,
                    department=department_id, manager=manager, tasktype=task_type,
                    dt_task=dt_task, area_count=json.dumps(area_count), img_url=img[:-1])
    if task_type in ["错架率抽样"]:
        Task.create(employee=employee_id, supervisor=assignor_id, code=code,
                    department=department_id, manager=manager, tasktype=task_type,
                    dt_task=dt_task, area_count=json.dumps(area_count), img_url=img[:-1])
    if task_type in ["分拣系统"] and bk_type == '停机':
        Task.create(employee=employee_id, supervisor=assignor_id, bk_type=bk_type, department=department_id,
                    manager=manager, tasktype=task_type, dt_task=dt_task, error_reason=error_reason,
                    message=message, downtime=downtime)
    if task_type in ["分拣系统"] and bk_type == '故障':
        Task.create(employee=employee_id, supervisor=assignor_id, bk_type=bk_type,
                    department=department_id, manager=manager, tasktype=task_type,
                    dt_task=dt_task, error_reason=error_reason, message=message, img_url=img[:-1])
    return jsonify(state=0, msg="提交成功，等待审核!")


@blueprint.route("/getAllUnauditedTask", methods=["POST"])
@login_required
def get_all_unaudited_task():
    """
    params: oneDate
    # 主管/经理查询所有的指定日期的未审核任务
    """
    if g.jwt["permission"] not in ["manager", "supervisor"]:
            return abort(400, "Lack of user rights!!")

    form = GetAllUncheckedTask(request.form)
    if not form.validate():
        return abort(400, "invalid params")

    user_uuid = g.jwt["uuid"]
    today = datetime.date.today()
    tomorrow = form.data['oneDate'] + datetime.timedelta(days=1)
    if g.jwt["permission"] == "manager":
        tasks = Task.select(Task, User).join(User).\
            where(Task.created >= form.data['oneDate'], Task.created <= tomorrow,
                  Task.status == "firstPass", Task.manager == user_uuid)
    else:
        tasks = Task.select(Task, User).join(User). \
            where(Task.created >= form.data['oneDate'], Task.created <= tomorrow,
                  Task.status == "notreviewed", Task.supervisor == user_uuid)

    arr_task = [{"uuid": task.uuid, "username": task.employee.username,
                 "task_type": task.tasktype, "created": task.created} for task in tasks]
    return jsonify(state=0, msg=arr_task)


@blueprint.route("/selectTaskDetails", methods=["POST"])
@login_required
def select_task_details():
    """
    params: uuid  #任务uuid
    查询任务详情
    """
    if g.jwt["permission"] not in ["manager", "supervisor"]:
            return abort(400, "Lack of user rights!!")

    form = SelectTaskDetails(request.form)
    if not form.validate():
        return abort(400, "invalid params")

    task = Task.select(User, Task).join(User).where(Task.uuid == form.data['uuid']).get()
    dict_task = {"username": task.employee.username, "submitTime": task.created,
                 "task": task.area_count, "imgAddress": task.img_url, "uuid": task.uuid}
    return jsonify(state=0, msg=dict_task)


@blueprint.route("/getAllUncheckedTask", methods=["POST"])
@login_required
def get_all_unchecked_task():
    """
    params: None
    主管/经理查询所有已审核的任务
    """
    if g.jwt["permission"] not in ["manager", "supervisor"]:
            return abort(400, "Lack of user rights!!")

    form = GetAllUncheckedTask(request.form)
    if not form.validate():
        return abort(400, "invalid params")

    today = datetime.date.today()
    tomorrow = form.data['oneDate'] + datetime.timedelta(days=1)
    if g.jwt["permission"] == "manager":
        tasks = Task.select(Task, User).join(User).\
            where(Task.created >= form.data['date'], Task.created <= tomorrow, (Task.status == "secondPass") |
                  (Task.status == "secondFailed"), Task.manager == g.jwt["uuid"])
    else:
        tasks = Task.select(Task, User).join(User). \
            where(Task.created >= form.data['oneDate'], Task.created <= tomorrow, (Task.status == "firstPass") |
                  (Task.status == "firstFailed"), Task.supervisor == g.jwt["uuid"])
    arr_task = [{"uuid": task.uuid, "username": task.employee.username,
                 "task_type": task.tasktype, "status": task.status} for task in tasks]
    return jsonify(state=0, msg=arr_task)


@blueprint.route("/reviewOneTask", methods=["POST"])
@login_required
def review_one_task():
    """
    params: uuid , status, reject_reasons  任务uuid, 审核状态
    主管/经理审核
    :return:
    """
    if g.jwt["permission"] not in ["manager", "supervisor"]:
            return abort(400, "Lack of user rights!!")
    form = ReviewOneTask(request.form)
    if not form.validate():
        return abort(400, "invalid params")

    if request.form['uuid'] == '':
        return abort(400, "invalid params")
    uuids = request.form['uuid'].split(',')
    reject_reasons = request.form['reject_reasons']

    if g.jwt["permission"] == "manager":
        if form.data['status'] == '0':
            state = 'secondPass'
            """审批一条任务"""
            if len(uuids) == 1:
                Task.update(status=state, ftrialtime=datetime.datetime.now()).where(Task.uuid == uuids[0]).execute()
            """批量审批"""
            if len(uuids) > 1:
                Task.update(status=state, ftrialtime=datetime.datetime.now()).where(Task.uuid << uuids).execute()
        else:
            state = 'secondFailed'
            """审批一条任务"""
            if len(uuids) == 1:
                Task.update(status=state, ftrialtime=datetime.datetime.now(),
                            reject_reasons=request.form['reject_reasons']).where(Task.uuid == uuids[0]).execute()
            """批量审批"""
            if len(uuids) > 1:
                Task.update(status=state, ftrialtime=datetime.datetime.now(),
                            reject_reasons=request.form['reject_reasons']).where(Task.uuid << uuids).execute()


    else:
        if form.data['status'] == '0':
            state = 'firstPass'
            """审批一条任务"""
            if len(uuids) == 1:
                Task.update(status=state, strialtime=datetime.datetime.now()).where(Task.uuid == uuids[0]).execute()
            """批量审批"""
            if len(uuids) > 1:
                Task.update(status=state, strialtime=datetime.datetime.now()).where(Task.uuid << uuids).execute()
        else:
            state = 'firstFailed'
            """审批一条任务"""
            if len(uuids) == 1:
                Task.update(status=state, strialtime=datetime.datetime.now(),
                            reject_reasons=request.form['reject_reasons']).where(Task.uuid == uuids[0]).execute()
            """批量审批"""
            if len(uuids) > 1:
                Task.update(status=state, strialtime=datetime.datetime.now(),
                            reject_reasons=reject_reasons).where(Task.uuid << uuids).execute()

    return jsonify(state=0, msg="审核完成")


def upload_head_img():
    img = ''
    files = request.files
    print(request.form)
    for file in files:
        file=files[file]
        filename = file.filename
        extension = filename.rsplit('.', 1)[1] if '.' in filename else None
        if not (extension and extension in current_app.config["HEADIMG_EXTENSIONS"]):
            return abort(400, "invalid params")
        tmp_file = "{}/{}.{}".format(current_app.config['UPLOAD_FOLDER'], uuid.uuid4(), extension)
        # 散列，不要都放到同一个bucket(目录)下

        object_name = "{}/{}.{}".format(int(time.time()) % 71, uuid.uuid4(), extension)
        # img = '%s%s%s%s' % (img, 'http://192.168.0.137:9000/headimg/', object_name, ',')
        img = '%s%s%s' % (img, object_name, ',')
        try:
            file.save(tmp_file)
            # TODO 需要压缩？
            # TODO mime?
            current_minio.fput_object("headimg", object_name, tmp_file)
        except Exception as e:
            logger.error("save headimg fail", exc_info=1)
            raise
        finally:
            os.unlink(tmp_file)  # 无论如何，删除临时文件
    return img



@blueprint.route("/getArea", methods=["POST"])
@login_required
def get_area():
    """
    选择区域
    params: tasktype
    """
    form = GetArea(request.form)
    if not form.validate():
        return abort(400, "invalid params")

    user = User.select(User.department).where(User.uuid == g.jwt["uuid"]).get()
    areas = Area.select(Area.parameter).where(Area.department == user.department)
    area_all = [area.parameter for area in areas]

    today = datetime.date.today()
    area_checked = []
    if len(area_all) > 0:
        tasks = Task.select(Task.area_count).where(Task.department==user.department, Task.created >= today,
                                                   Task.status == "secondPass",
                                                   Task.tasktype == request.form['tasktype'])
        for task in tasks:
            for area in json.loads(task.area_count):
                area_checked.append(json.loads(task.area_count)[area]["area_name"])

    area = {"area_all": area_all, "area_checked": area_checked}
    return jsonify(state=0, msg=area)
