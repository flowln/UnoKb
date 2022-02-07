// Set to 1 (default) if you're using an LCD display
// Set to 0 if you don't want this support
#define USE_LCD 1
#define DEBUG 0

#if USE_LCD

#include <LiquidCrystal.h>

LiquidCrystal lcd(2, 3, 4, 5, 6, 7);
const int lcd_width = 16;

#endif // USE_LCD

volatile int input_states = 0;

const char button_1 = 8;
const char button_2 = 9;
const char button_3 = 10;
const char button_4 = 11;
const char button_mode = 12;

#if USE_LCD
/* Waits for a host to provide us with a set of functions the buttons will do.
 * This is only required because of the LCD display, since the arduino has no
 * information on what exactly each button will do in the end.*/
const char** requestMode()
{
    const char* first_line =  "  Waiting for"; // 13 chars
    String second_line = "  mode info   "; // 14 chars

    lcd.clear();
    lcd.setCursor(0,0);
    lcd.print(first_line);
    lcd.setCursor(0,1);
    lcd.print(second_line.c_str());
    lcd.setCursor(0,0);

    char** modes = new char*[4];
    for(int i = 0; i < 4; i++)
        modes[i] = new char[17];
    
    char mode_count = 0;
    char idle_timer = 0;

    const char points_pos = second_line.length() - 3; // Starting position of the dots in the second line
    char points_i = 0; // Offset of the dot in the second line

    while(mode_count < 4){
        // Read serial input for modes
        if(Serial.readBytesUntil('\n', modes[mode_count], 17)){
            // If received message == "mode_setup", reset the mode_count
            if(!strcmp(modes[mode_count], "mode_setup"))
                mode_count = 0; 
            else
                mode_count += 1; 
        }

        // If the arduino is not receiving anything, keep
        // sending the mode_setup message periodically.
        if(mode_count == 0 && idle_timer++ >= 16){
            idle_timer = 0;
            Serial.println("mode_changed=0");
        }

        if(idle_timer % 5 == 0){
            // Animate the dots blinking ;)
            if(second_line[points_pos + points_i] == ' ')
                second_line[points_pos + points_i] = '.';
            else
                second_line[points_pos + points_i] = ' ';

            points_i = (points_i + 1) % 3;

            // Easier to just print the whole line instead of only the dots :P
            lcd.setCursor(0,1);
            lcd.print(second_line.c_str());
        }
    }

    return modes;
}

void changeMode()
{
    const char** modes = requestMode();

    lcd.clear();
    lcd.setCursor(0,0);
    lcd.print(modes[0]);
    lcd.setCursor(lcd_width - strlen(modes[1]), 0);
    lcd.print(modes[1]);
    lcd.setCursor(0, 1);
    lcd.print(modes[2]);
    lcd.setCursor(lcd_width - strlen(modes[3]), 1);
    lcd.print(modes[3]);

    for(int i = 0; i < 4; i++)
        delete modes[i];
    delete modes;
}
#else 
void changeMode(){} // noop if not using LCD
#endif //USE_LCD

void setup() 
{
    Serial.begin(9600);
    Serial.setTimeout(50);
   
#if USE_LCD
    lcd.begin(16, 2);
    changeMode();
#endif

    pinMode(button_1,  INPUT_PULLUP);
    pinMode(button_2,  INPUT_PULLUP);
    pinMode(button_3,  INPUT_PULLUP);
    pinMode(button_4,  INPUT_PULLUP);
    pinMode(button_mode, INPUT_PULLUP);
}

/* Converts a pin number to the button
 * it is connected to. eg: pin 8 -> button 1 */
char pinNumberToButton(char pin_number)
{
    switch(pin_number){
    case button_1:
        return 1;
    case button_2:
        return 2;
    case button_3:
        return 3;
    case button_4:
        return 4;
    default:
        return 0;
    }
}

void readInput(char pin_number)
{
    bool is_pressed = !digitalRead(pin_number);
    int mask = 0x1 << (pin_number - 1);
    bool was_pressed = input_states & mask;

#if DEBUG
    Serial.print("Debug to port number ");
    Serial.println(pin_number, DEC);

    Serial.print("State: ");
    Serial.println(was_pressed, BIN);
    
    Serial.print("Mask: ");
    Serial.println(mask, BIN);
#endif

    if(was_pressed && !is_pressed){
        input_states &= 0xffff - mask;
        if(pin_number != button_mode){
            Serial.print("btn_released=");
            Serial.println(pinNumberToButton(pin_number), DEC);
            Serial.flush();
        }
    }
    else if(is_pressed){
        if(!was_pressed){
            if(pin_number == button_mode){
                Serial.print("mode_changed=");
                Serial.println(1, DEC);
                Serial.flush();
                changeMode();
            }
            else{
                Serial.print("btn_pressed=");
                Serial.println(pinNumberToButton(pin_number), DEC);
                Serial.flush();
            }
        }

        input_states |= mask;
    }
}

void checkInbox()
{
    if(Serial.available() == 0)
        return;

    String received = Serial.readStringUntil('\n');
    if(received == "mode_setup"){
        changeMode();
    }
#if USE_LCD
    else if(received == "host_disconnect"){
        changeMode();
    }
#endif

}

void loop() 
{
    // 50ms on average
    checkInbox();

    // Not using interrupts here because I need to do de-bouncing in software.
    // If you don't have such a problem, feel free to use them and
    // save some latency.

    readInput(button_1);
    readInput(button_2);
    readInput(button_3);
    readInput(button_4);
    readInput(button_mode);
}

