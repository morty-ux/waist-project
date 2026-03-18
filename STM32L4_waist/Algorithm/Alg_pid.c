#include "Alg_pid.h"
#include <math.h>


void PID_Init(PID_Controller* pid, float p, float i, float d, float dt, float max, float min, float dead_zone) {
    if (pid == NULL) return;
    pid->kp = p;
    pid->ki = i;
    pid->kd = d;
    pid->dt = (dt > 0.0f) ? dt : 0.01f; // 防止 dt 为 0
    pid->out_max = max;
    pid->out_min = min;
    pid->integral_limit = max * 0.5f;
		pid->dead_zone = dead_zone;
    
    pid->error_curr = 0;
    pid->error_last = 0;
    pid->error_sum = 0;
}

float PID_Compute(PID_Controller* pid, float measure) {
    if (pid == NULL) return 0.0f;
	
    pid->error_curr = pid->target - measure;

	  // 如果误差的绝对值小于设定的死区，则认为已经到达目标
    if (fabs(pid->error_curr) <= pid->dead_zone) {
        pid->error_sum = 0;   // 清空积分，防止静态误差累积造成抵达后的震荡
        pid->error_last = 0;
        pid->output = 0;
        return 0.0f;
    }
	
    // 积分计算: Integral = Integral + error * dt
    pid->error_sum += pid->error_curr * pid->dt;
    
    // 积分抗饱和限幅
    if (pid->error_sum > pid->integral_limit) pid->error_sum = pid->integral_limit;
    if (pid->error_sum < -pid->integral_limit) pid->error_sum = -pid->integral_limit;

    // 微分计算: Derivative = (error - last_error) / dt
    float derivative = (pid->error_curr - pid->error_last) / pid->dt;

    // 最终输出
    pid->output = (pid->kp * pid->error_curr) + 
                  (pid->ki * pid->error_sum) + 
                  (pid->kd * derivative);

    pid->error_last = pid->error_curr;

    // 输出限幅
    if (pid->output > pid->out_max) pid->output = pid->out_max;
    if (pid->output < -pid->out_max) pid->output = -pid->out_max;
		
    return -pid->output;
}


/**
 * @brief 设置目标值
 */
void PID_SetTarget(PID_Controller* pid, float target) {
    if (pid == NULL) return;
    pid->target = target;
}
