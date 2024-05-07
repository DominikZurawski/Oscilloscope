/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file           : main.c
  * @brief          : Main program body
  ******************************************************************************
  * @attention
  *
  * Copyright (c) 2024 STMicroelectronics.
  * All rights reserved.
  *
  * This software is licensed under terms that can be found in the LICENSE file
  * in the root directory of this software component.
  * If no LICENSE file comes with this software, it is provided AS-IS.
  *
  ******************************************************************************
  */
/* USER CODE END Header */
/* Includes ------------------------------------------------------------------*/
#include "main.h"
#include "adc.h"
#include "dma.h"
#include "tim.h"
#include "usart.h"
#include "gpio.h"

/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */

#include <stdio.h>

#define ARM_MATH_CM4
#include "arm_math.h"


/* USER CODE END Includes */

/* Private typedef -----------------------------------------------------------*/
/* USER CODE BEGIN PTD */

/* USER CODE END PTD */

/* Private define ------------------------------------------------------------*/
/* USER CODE BEGIN PD */

/* USER CODE END PD */

/* Private macro -------------------------------------------------------------*/
/* USER CODE BEGIN PM */

/* USER CODE END PM */

/* Private variables ---------------------------------------------------------*/

/* USER CODE BEGIN PV */

#define FFT_BUFFER_SIZE 2048
#define SAMPLE_RATE 80000 // Częstotliwość próbkowania ADC w Hz
volatile static uint32_t adc_value[2][FFT_BUFFER_SIZE]; // Bufor do przechowywania danych z dwóch kanałów
uint32_t buffer1[FFT_BUFFER_SIZE];
uint32_t buffer2[FFT_BUFFER_SIZE];
float32_t fft_output_1[FFT_BUFFER_SIZE];
float32_t fft_output_2[FFT_BUFFER_SIZE];
float32_t fft_magnitude_1[FFT_BUFFER_SIZE]; // Tablica do przechowywania magnitudy FFT dla kanału 1
float32_t fft_magnitude_2[FFT_BUFFER_SIZE]; // Tablica do przechowywania magnitudy FFT dla kanału 2
arm_rfft_fast_instance_f32 fft_handler; // Inicjalizacja instancji FFT



#define DATA_SIZE 100 // Rozmiar bufora danych do wysłania przez UART
char data[DATA_SIZE]; // Bufor danych do wysłania przez UART
float32_t fft_output_1[FFT_BUFFER_SIZE];
float32_t fft_output_2[FFT_BUFFER_SIZE];


uint8_t Buffer_FFT_Status = 0; // Zmienna do śledzenia statusu bufora FFT
uint8_t Calculation_finished = 1; // Zmienna do śledzenia, czy obliczenia zostały zakończone

int buf_index = 0;
//uint16_t data[20];
volatile static uint16_t value[2];


/* USER CODE END PV */

/* Private function prototypes -----------------------------------------------*/
void SystemClock_Config(void);
/* USER CODE BEGIN PFP */
void process_fft_data(uint32_t *adc_data, float32_t *fft_output, float32_t *fft_magnitude, uint32_t fft_size, float sample_rate);
/* USER CODE END PFP */

/* Private user code ---------------------------------------------------------*/
/* USER CODE BEGIN 0 */

int __io_putchar(int ch)
{
    if (ch == '\n') {
        uint8_t ch2 = '\r';
        HAL_UART_Transmit(&huart2, &ch2, 1, HAL_MAX_DELAY);
    }

    HAL_UART_Transmit(&huart2, (uint8_t*)&ch, 1, HAL_MAX_DELAY);
    return 1;
}
void process_fft_data(uint32_t *adc_data, float32_t *fft_output, float32_t *fft_magnitude, uint32_t fft_size, float sample_rate)
{
	//if(Buffer_FFT_Status==1)
	      //{
	// 1. Stosuje FFT na dane z ADC


    arm_rfft_fast_f32(&fft_handler, (float32_t*)adc_data, fft_output, 0);

    // 2. Wydzielenie wartości rzeczywistej i urojonej
        float32_t real_values[fft_size/2];
        float32_t imag_values[fft_size/2];
        for (int i = 0; i < fft_size/2; i++) {
            real_values[i] = fft_output[2*i];
            imag_values[i] = fft_output[2*i + 1];
        }

    // 3. Oblicza przesunięcie fazowe dla każdego prążka
        float32_t phase_shift[fft_size/2];
        for (int i = 0; i < fft_size/2; i++) {
            phase_shift[i] = atan2(imag_values[i], real_values[i]);
        }

    // 4. Oblicza moduł (magnitudę) FFT z wartości rzeczywistej i urojonej dla każdego z prążków
    arm_cmplx_mag_f32(fft_output, fft_magnitude, fft_size);

    // 5. Znajduje dominującą częstotliwość
    uint32_t maxIndex;
    float32_t maxValue;
    arm_max_f32(fft_magnitude, fft_size, &maxValue, &maxIndex);
    float32_t dominant_frequency = (float)maxIndex * (sample_rate / fft_size);

    // 6. Przesunięcie fazowe maksymalnego prążka
    float32_t max_phase_shift = phase_shift[maxIndex];
    printf("Przesunięcie fazowe maksymalnego prążka: %f rad\n", max_phase_shift);
    printf("Dominująca częstotliwość: %f Hz\n", dominant_frequency);

    // 7. Filtruj wyniki FFT
    /*
    float32_t threshold = 0.5; // Ustaw próg na odpowiednią wartość
    for (int i = 0; i < FFT_BUFFER_SIZE; i++) {
        if (fft_magnitude[i] < threshold) {
            fft_magnitude[i] = 0;
        }
    }*/
    /*Informacja o zakończeniu obliczeń*/
    //Calculation_finished=1;
    /*Zerowanie wartości maksymalnej*/
    //maxValue=0;
}
//}

void collect_adc_data() {

	buffer1[buf_index] = value[0];
	//printf("%u \n", value[0]);
	buffer2[buf_index] = value[1];
	buf_index = (buf_index + 1) % FFT_BUFFER_SIZE;

}

//uint16_t data[20];
//volatile static uint16_t value[2];
//HAL_UART_TxCpltCallback //analogiczna funkcja, dane są wysyłane po zakończeniu poprzedniej transmisji
void HAL_UART_TxHalfCpltCallback(UART_HandleTypeDef *huart)	//dane są przygotowywane w połowie wysyłania poprzedniej transmisji
{
	//collect_adc_data();
	//sprintf(data, "CH1 %d,CH2 %d\r\n", value[0], value[1]);
	//sprintf(data, "%d\r\n", value[1]);
	//data[0] = "%u\n" + data[0];

}
/*
void print_buffer_in_one_line(uint32_t* buffer, size_t size) {
    printf("[");
    for (int i = 0; i < size; i++) {
        printf("%u", buffer[i]);
        if (i < size - 1) {
            printf(", ");
        }
    }
    printf("]\n");
}*/

void HAL_ADC_ConvCpltCallback(ADC_HandleTypeDef* hadc) //wywoływana gdy konwersja ADC jest zakończona
{

	if(hadc->Instance == ADC1)
	    {
		collect_adc_data();
		//printf("Dominująca częstotliwość: %d Hz\n", buf_index);
		if (buf_index == FFT_BUFFER_SIZE-1){
			//process_fft_data(buffer1, fft_output_1, fft_magnitude_1, FFT_BUFFER_SIZE, SAMPLE_RATE);
			//process_fft_data(buffer2, fft_output_2, fft_magnitude_2, FFT_BUFFER_SIZE, SAMPLE_RATE);

			//print_buffer_in_one_line(buffer1, FFT_BUFFER_SIZE);
		}


	        //if(Calculation_finished==1 )
	        //{
	        //    Calculation_finished=0;
	        //    Buffer_FFT_Status=1;
	            //process_fft_data(adc_value[0], fft_output_1, fft_magnitude_1, FFT_BUFFER_SIZE, SAMPLE_RATE);
	        //}

	        //process_fft_data(adc_value[0], fft_output_1, fft_magnitude_1, FFT_BUFFER_SIZE, SAMPLE_RATE);
	        //process_fft_data(adc_value[1], fft_output_2, fft_magnitude_2, FFT_BUFFER_SIZE, SAMPLE_RATE);

	        //snprintf(data, DATA_SIZE, "CH1 %d,CH2 %d\r\n", fft_output_1, fft_output_2);
			//TUTAJ UART
			//snprintf(data, DATA_SIZE, "CH1 %d\r\n", value[0]);
			//snprintf(data, DATA_SIZE, "%d, %d, %d, %d\r\n", value[0], value[1], value[0], value[1]);
	        snprintf(data, DATA_SIZE, "CH1 %d,CH2 %d\r\n", value[0], value[1]);
	        // Wyślij dane przez UART
	        HAL_UART_Transmit_DMA(&huart2, (uint8_t*)data, sizeof(data));
	    }
}



/* USER CODE END 0 */

/**
  * @brief  The application entry point.
  * @retval int
  */
int main(void)
{

  /* USER CODE BEGIN 1 */

  /* USER CODE END 1 */

  /* MCU Configuration--------------------------------------------------------*/

  /* Reset of all peripherals, Initializes the Flash interface and the Systick. */
  HAL_Init();

  /* USER CODE BEGIN Init */

  /* USER CODE END Init */

  /* Configure the system clock */
  SystemClock_Config();

  /* USER CODE BEGIN SysInit */

  /* USER CODE END SysInit */

  /* Initialize all configured peripherals */
  MX_GPIO_Init();
  MX_DMA_Init();
  MX_USART2_UART_Init();
  MX_ADC1_Init();
  MX_TIM3_Init();
  /* USER CODE BEGIN 2 */

  /* Inicjalizacja instancji FFT */
  arm_rfft_fast_init_f32(&fft_handler, FFT_BUFFER_SIZE);

#define LINE_MAX_LENGTH	80

static char line_buffer[LINE_MAX_LENGTH + 1];
static uint32_t line_length;

void line_append(uint8_t value)
{
	if (value == '\r' || value == '\n') {
		// odebraliśmy znak końca linii
		if (line_length > 0) {
			// dodajemy 0 na końcu linii
			line_buffer[line_length] = '\0';
			// przetwarzamy dane
			if (strcmp(line_buffer, "on") == 0) {
				HAL_GPIO_WritePin(LD2_GPIO_Port, LD2_Pin, GPIO_PIN_SET);
			} else if (strcmp(line_buffer, "off") == 0) {
				HAL_GPIO_WritePin(LD2_GPIO_Port, LD2_Pin, GPIO_PIN_RESET);
			} else {
				printf("Nieznane polecenie: %s\n", line_buffer);
			}
			// zaczynamy zbieranie danych od nowa
			line_length = 0;
		}
	}
	else {
		if (line_length >= LINE_MAX_LENGTH) {
			// za dużo danych, usuwamy wszystko co odebraliśmy dotychczas
			line_length = 0;
		}
		// dopisujemy wartość do bufora
		line_buffer[line_length++] = value;
	}
}


  /* USER CODE END 2 */

  /* Infinite loop */
  /* USER CODE BEGIN WHILE */

HAL_ADCEx_Calibration_Start(&hadc1, ADC_SINGLE_ENDED);
HAL_TIM_Base_Start(&htim3);
HAL_ADC_Start_DMA(&hadc1, (uint32_t*)value, 2);
//HAL_ADC_Start_DMA(&hadc1, (uint32_t*)adc_value, 2 * FFT_BUFFER_SIZE);

HAL_TIM_PWM_Start(&htim3, TIM_CHANNEL_3);

//uint32_t *channel_1_data = adc_value[0];
//uint32_t *channel_2_data = adc_value[1];



while (1)
{

	//HAL_UART_Transmit_DMA(&huart2, (uint8_t*)data, sizeof(data));

	  //uint8_t message;

	  //if (HAL_UART_Receive(&huart2, &message, 1, 0) == HAL_OK)
	  	//line_append(message);




    /* USER CODE END WHILE */

    /* USER CODE BEGIN 3 */
}
  /* USER CODE END 3 */
}

/**
  * @brief System Clock Configuration
  * @retval None
  */
void SystemClock_Config(void)
{
  RCC_OscInitTypeDef RCC_OscInitStruct = {0};
  RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};

  /** Configure the main internal regulator output voltage
  */
  if (HAL_PWREx_ControlVoltageScaling(PWR_REGULATOR_VOLTAGE_SCALE1) != HAL_OK)
  {
    Error_Handler();
  }

  /** Configure LSE Drive Capability
  */
  HAL_PWR_EnableBkUpAccess();
  __HAL_RCC_LSEDRIVE_CONFIG(RCC_LSEDRIVE_LOW);

  /** Initializes the RCC Oscillators according to the specified parameters
  * in the RCC_OscInitTypeDef structure.
  */
  RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_LSE|RCC_OSCILLATORTYPE_MSI;
  RCC_OscInitStruct.LSEState = RCC_LSE_ON;
  RCC_OscInitStruct.MSIState = RCC_MSI_ON;
  RCC_OscInitStruct.MSICalibrationValue = 0;
  RCC_OscInitStruct.MSIClockRange = RCC_MSIRANGE_6;
  RCC_OscInitStruct.PLL.PLLState = RCC_PLL_ON;
  RCC_OscInitStruct.PLL.PLLSource = RCC_PLLSOURCE_MSI;
  RCC_OscInitStruct.PLL.PLLM = 1;
  RCC_OscInitStruct.PLL.PLLN = 40;
  RCC_OscInitStruct.PLL.PLLP = RCC_PLLP_DIV7;
  RCC_OscInitStruct.PLL.PLLQ = RCC_PLLQ_DIV2;
  RCC_OscInitStruct.PLL.PLLR = RCC_PLLR_DIV2;
  if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK)
  {
    Error_Handler();
  }

  /** Initializes the CPU, AHB and APB buses clocks
  */
  RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK|RCC_CLOCKTYPE_SYSCLK
                              |RCC_CLOCKTYPE_PCLK1|RCC_CLOCKTYPE_PCLK2;
  RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
  RCC_ClkInitStruct.AHBCLKDivider = RCC_SYSCLK_DIV1;
  RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV1;
  RCC_ClkInitStruct.APB2CLKDivider = RCC_HCLK_DIV1;

  if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_4) != HAL_OK)
  {
    Error_Handler();
  }

  /** Enable MSI Auto calibration
  */
  HAL_RCCEx_EnableMSIPLLMode();
}

/* USER CODE BEGIN 4 */

/* USER CODE END 4 */

/**
  * @brief  This function is executed in case of error occurrence.
  * @retval None
  */
void Error_Handler(void)
{
  /* USER CODE BEGIN Error_Handler_Debug */
/* User can add his own implementation to report the HAL error return state */
__disable_irq();
while (1)
{
}
  /* USER CODE END Error_Handler_Debug */
}

#ifdef  USE_FULL_ASSERT
/**
  * @brief  Reports the name of the source file and the source line number
  *         where the assert_param error has occurred.
  * @param  file: pointer to the source file name
  * @param  line: assert_param error line source number
  * @retval None
  */
void assert_failed(uint8_t *file, uint32_t line)
{
  /* USER CODE BEGIN 6 */
/* User can add his own implementation to report the file name and line number,
   ex: printf("Wrong parameters value: file %s on line %d\r\n", file, line) */
  /* USER CODE END 6 */
}
#endif /* USE_FULL_ASSERT */
