<!DOCTYPE html>
<!--
A frame for displaying the letter passed from letters.php as $_GET["filename"], or the latest file in the index.
15.6.2016
-->

<html lang="en">
	<head>
		<title>Letter</title>
		<meta charset="UTF-8" />
		<meta name="description" content="Letter templates for busy people." />
		<link rel="icon" type="image/x-icon" href="./favicon.ico" />

		<!-- bootstrap -->
		<meta name="viewport" content="width=device-width, initial-scale=1">
		<link rel="stylesheet" href="http://maxcdn.bootstrapcdn.com/bootstrap/3.3.5/css/bootstrap.min.css">
		<script src="https://ajax.googleapis.com/ajax/libs/jquery/1.11.3/jquery.min.js"></script>
		<script src="http://maxcdn.bootstrapcdn.com/bootstrap/3.3.5/js/bootstrap.min.js"></script>

		<link rel="stylesheet" href="./active.css">


	</head>
	<body>

	<?php
		//filename of the letter to display as passed from letters.php or empty if active.php was opened directly
		$filename = $_GET['filename'];
		$file_string = file_get_contents($filename);

		// if nothing was passed as $_GET, read the latest file from the index
		if (empty($filename)) {
			$base = "letters/";
			$files = glob($base . "*.txt");
			// use usort to sort by time modified
			usort($files, function($a, $b){
				return filemtime($base . $a) < filemtime($base . $b);
			});
			$file_string = file_get_contents($files[0]);
		}
	?>


	<div class="container">

		<div class="row">

			<!-- left margin -->
			<div class="col-md-2">
			</div>
			

			<!-- middle section for content -->
			<div class="col-md-8" id="letter">
				<div class="page-header">
				 	<h1>Letters from Twitter</h1> 
				 	<p>Letter and form templates filled with input taken from Twitter</p> 
				</div>

				<!-- navbar for buttons to linking letter/next template -->
				<nav class="navbar navbar-default">
				 	<div class="container-fluid">
					    <ul class="nav navbar-nav">
					      	<li><a href="http://lajanki.mbnet.fi/">Index</a></li>
					      	<li><a href="http://lajanki.mbnet.fi/date_profiler/profiler.php">Date profiles</a></li>
					      	<li><a href="https://twitter.com/vocal_applicant">@vocal_applicant</a></li>
					    </ul>
				  	</div>
				</nav>

				<!-- actual letter, new div for background -->
				<div id="letter-content">
				<?php
					echo $file_string;
				 ?>
				 </div>
			</div>

			<!-- right margin -->
			<div class="col-md-2">
			</div>
			

		<!-- row -->
		</div>

		<!-- new row for bottom part of the page -->
		<div class="row">
			<p>Background image: <br />
			<a href="https://pixabay.com/">Pixabay.com</a></p>
		</div>

	<!-- container -->
	</div>

		
    </body>
</html>





