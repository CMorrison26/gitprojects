//Uncommenting the following line
//will upset Javascript and keep the message from being printed
//write("Welcome to my gallery!")
const testmessage = "Hello and welcome to the gallery. Text generated via Javascript";
const outputElementTest = document.getElementById("test-text");

//If the element exists: Use the following
if (outputElementTest)
{
    outputElementTest.textContent = testmessage;
}
