// Synthetic 8 x 10 bright-on-dark plate-like image for alignment testing.
// Uses only built-in ImageJ macro functions.

rows = 8;
cols = 10;
imgW = 1300;
imgH = 1000;
leftX = 180;
rightX = 1120;
leftTopY = 155;
rightTopY = 170;
rowSpacing = 95;
dotW = 48;
dotH = 48;

newImage("Synthetic grid plate", "8-bit black", imgW, imgH, 1);
setColor("white");

for (r = 0; r < rows; r++) {
    for (c = 0; c < cols; c++) {
        u = c / (cols - 1);
        cx = leftX + u * (rightX - leftX);
        rowYLeft = leftTopY + r * rowSpacing;
        rowYRight = rightTopY + r * rowSpacing;
        cy = rowYLeft + u * (rowYRight - rowYLeft);
        fillOval(cx - dotW / 2, cy - dotH / 2, dotW, dotH);
    }
}

// Start with a reusable tall first-column ROI; move the same ROI to the last column.
makeRectangle(leftX - 38, leftTopY - 48, 76, (rows - 1) * rowSpacing + 96);
showStatus("Synthetic grid ready: run full_column_alignment.ijm");
