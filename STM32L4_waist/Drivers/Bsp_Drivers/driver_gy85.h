#ifndef __DRIVER_ACTUATOR_H__
#define __DRIVER_ACTUATOR_H__

#include <stdint.h>
#include <stdbool.h>
#include "tim.h" 

#ifndef NULL
#define NULL ((void *)0)
#endif

// --- 推杆物理参数宏 ---
#define ACTUATOR_ADC_MIN          000       // 对应 100mm
#define ACTUATOR_ADC_MAX          4096    // 对应 0mm
#define ACTUATOR_MAX_STROKE       100     // 最大行程 100mm

/**
 * @brief ADC 转换为行程 (mm) - 浮点版本
 * 公式: (MAX_ADC - current_ADC) * (Max_Stroke / Total_ADC_Range)
 */
#define ADC_TO_MM_FLOAT(adc) \
    ((float)((int32_t)ACTUATOR_ADC_MAX - (int32_t)(adc)) * ((float)ACTUATOR_MAX_STROKE / (float)(ACTUATOR_ADC_MAX - ACTUATOR_ADC_MIN)))

// 推杆目标值设定
typedef struct {
	float RbTarget;
	float RfTarget;
	float LbTarget;
	float LfTarget;
} ActuatorTarget;

// 推杆运动方向
typedef enum {
    ACTUATOR_STOP = 0,
    ACTUATOR_FORWARD,
    ACTUATOR_BACKWARD
} ActuatorDirType;

typedef struct {
    // 硬件配置 (集中初始化)
    void* tim_handle;    // 定时器句柄 (如 &htim1)
    uint32_t channel_a;     // 通道 A (如 TIM_CHANNEL_1)
    uint32_t channel_b;     // 通道 B (如 TIM_CHANNEL_2)
    
    // 参数配置
    uint32_t max_duty;      // PWM 满载值（限幅上限）
    
    // 运行状态
    ActuatorDirType dir;
    uint32_t current_duty;
    uint16_t current_adc;
		float current_pos_mm;
} ActuatorDevice;

// 函数接口
void Actuator_Init(ActuatorDevice* dev, void* tim_ptr, uint32_t ch_a, uint32_t ch_b, uint32_t max_duty);
void Actuator_Control(ActuatorDevice* dev, int16_t duty) ;
void Actuator_UpdateFeedback(ActuatorDevice* dev, uint16_t adc_val);

#endif