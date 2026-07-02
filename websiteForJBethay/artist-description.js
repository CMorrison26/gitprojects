const ARTISTMESSAGE = "Janet Bethay is a modern abstract artist based in Cocoa, Florida" +
" whose work explores spontaneity and emotional expression." +
" Her artwork is influenced by Flora Bowley (Portland, Oregon) whose process encourages" +
" fluidity is activating the canvas with methods such as paint dripping and use of markings.\n" +
"\n" +
"Janet's process of painting includes rotating the canvas' orientation in which she adds" +
" layers of bold colors, geometric patterns, revealing the depth of the painting." +
" There are multiple ways to interpret her abstract paintings which invites the viewer" +
" to engage playfully with the canvas.";

const OUTPUTELEMENT = document.getElementById("artistDescription");

//If the element exists: Use the following
if (OUTPUTELEMENT)
{
    OUTPUTELEMENT.textContent = ARTISTMESSAGE;
}
