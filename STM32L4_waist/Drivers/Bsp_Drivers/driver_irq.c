#include "main.h"
#include "stm32l4xx_hal_adc.h"
#include "stm32l4xx_hal_uart.h"
#include "usart.h"

#include "adc.h"
#include "driver_actuator.h"
#include "driver_shell.h"
#include "driver_ESP01s.h"

extern ActuatorDevice ActuatorRF;
extern ActuatorDevice ActuatorRB;
extern volatile uint16_t AdcRec[2];

extern UART_HandleTypeDef hlpuart1;
extern uint8_t shell_buff[64];
extern ESP8266_Device esp8266;

/**
  * @brief  Conversion DMA half-transfer callback in non-blocking mode.
  * @param hadc ADC handle
  * @retval None
  */
void HAL_ADC_ConvCpltCallback(ADC_HandleTypeDef *hadc)
{
    if (hadc == &hadc1) {
			Actuator_UpdateFeedback(&ActuatorRF,AdcRec[0]);
			Actuator_UpdateFeedback(&ActuatorRB,AdcRec[1]);
    }
}


/**
  * @brief  Reception Event Callback (Rx event notification called after use of advanced reception service).
  * @param  huart UART handle
  * @param  Size  Number of data available in application reception buffer (indicates a position in
  *               reception buffer until which, data are available)
  * @retval None
  */
void HAL_UARTEx_RxEventCallback(UART_HandleTypeDef *huart, uint16_t Size)
{
	if(huart->Instance == LPUART1){
		HAL_UARTEx_ReceiveToIdle_DMA(&hlpuart1, shell_buff, sizeof(shell_buff));
		Shell_GetArgsFromISR((char*)shell_buff, Size);
	}
}

void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)
{
  /* Prevent unused argument(s) compilation warning */
	ESP8266_RxCpltCallback(&esp8266);
}