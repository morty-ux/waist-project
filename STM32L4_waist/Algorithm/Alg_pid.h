#ifndef __ALG_PID_H__
#define __ALG_PID_H__

#include <stdint.h>

#ifndef NULL
#define NULL ((void *)0)
#endif


typedef struct {
    // PID 参数 (物理意义上的 Kp, Ki, Kd)
    float kp;
    float ki;
    float kd;

    // 采样周期 (秒)
    float dt;

    // 误差记录
    float target;
    float error_curr;
    float error_last;
    float error_sum;

    // 输出限幅
    float out_max;
    float out_min;
    float integral_limit;
	
	
		// 死区控制
		float dead_zone;

    float output;
} PID_Controller;

// 初始化时增加 dt 参数
void PID_Init(PID_Controller* pid, float p, float i, float d, float dt, float max, float min, float dead_zone);
float PID_Compute(PID_Controller* pid, float measure);
void PID_SetTarget(PID_Controller* pid, float target);

#endif

